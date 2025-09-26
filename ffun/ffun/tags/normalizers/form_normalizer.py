from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base
from lemminflect import getLemma, getInflection
from typing import Literal
import numpy as np
import spacy
from spacy.cli import download


# TODO: not so good solution, refactor
def ensure_model(name: str,
                 disable=["parser", "ner", "senter", "textcat", "tagger", "lemmatizer"]) -> spacy.language.Language:
    try:
        return spacy.load(name, disable=disable)
    except OSError:
        download(name)
        return spacy.load(name, disable=disable)


# TODO: comment/mark application of each guard
# TODO: maybe organize guards in a lists, if it makes sense
# TODO: tests
# TODO: test performance
# TODO: add to configs
class Normalizer(base.Normalizer):
    """Normalizes forms of tag parts.

    Currently normalizes only time, but can be extended in the future.

    The algorithm:

    - Place the last part of the tag in singular form (if possible).
    - For each other part of the tag, starting from the right:
      - Let's imaging we have tag @a-b-tail
      - Create two tag candidates: `@singular(b)-tail` & `@plural(b)-tail`
      - Chose the tag, that has the highest similarity with @c, new tag will become tail
      - Now we normalize tag @a-tail (got to the next loop iteration)

    We compute similarity using cosine distance between word vectors.

    We singularize the last part of the tag because it singularization produces better results than pluralization:

    - We keep consistent proper names like `@charles-darwin`, `@new-york`
    - We do not make bad word forms like `informations`, `learnings`, etc.
    - => We do not need to implement prosessing of multiple corner cases .
    """

    __slots__ = ('_singular_cache', '_plural_cache', '_nlp')

    def __init__(self) -> None:
        # TODO: we should periodically trim caches
        self._singular_cache: dict[str, tuple[str]] = {}
        self._plural_cache: dict[str, tuple[str]] = {}

        # TODO: parametrize
        # TODO: when to load model?
        # TODO: do not forget about loading in both dev/prod docker containers
        self._nlp = ensure_model("en_core_web_lg")

    def _get_word_base_forms(self, word: str) -> tuple[str]:
        for upos in ('NOUN', 'VERB', 'ADJ', 'ADV'):
            lemmas = getLemma(word, upos=upos)

            if lemmas:
                return tuple(lemmas)

        return (word,)

    def get_word_base_forms(self, word: str) -> tuple[str]:
        if word in self._singular_cache:
            return self._singular_cache[word]

        base_forms = self._get_word_base_forms(word)

        self._singular_cache[word] = base_forms

        return base_forms

    def _get_word_plural_forms(self, word: str) -> tuple[str]:
        forms = getInflection(word, tag='NNS')

        if forms:
            return tuple(forms)

        return (word,)

    def get_word_plural_forms(self, word: str) -> tuple[str]:
        if word in self._plural_cache:
            return self._plural_cache[word]

        plural_forms = self._get_word_plural_forms(word)

        self._plural_cache[word] = plural_forms

        return plural_forms

    def get_main_tail_form(self, word: str) -> str:
        base_forms = self.get_word_base_forms(word)

        if len(base_forms) == 1:
            return base_forms[0]

        # In case we got smth like axes -> axis, axe, we better keep original word
        # TODO: maybe we can do better, for example, but producing a variant of tag for each base tail
        print('multiple base forms for tail:', word, '->', base_forms)
        return word

    def get_word_forms(self, word: str) -> list[str]:  # noqa: CCR001
        if len(word) <= 2:
            return [word]

        if any(c.isdigit() for c in word):
            return [word]

        base_forms = list(self.get_word_base_forms(word))

        print('!base forms for', word, ':', base_forms)

        forms = list(base_forms)

        for base_form in base_forms:
            for plural_form in self.get_word_plural_forms(base_form):
                print('!plural form for', base_form, ':', plural_form)
                if plural_form not in forms:
                    forms.append(plural_form)
        print('!returned forms for', word, ':', forms)
        return forms

    # TODO: cache
    def base_vector(self) -> np.ndarray:
        return np.zeros(self._nlp.vocab.vectors_length, dtype=np.float32)

    def unit_vector(self, word: str) -> np.ndarray:
        try:
            vector = self._nlp.vocab.get_vector(word)
        except Exception:
            vector = None

        if vector is None or vector.shape[0] == 0:
            return self.base_vector()

        norm = np.linalg.norm(vector)

        if norm == 0.0:
            return self.base_vector()

        return (vector / norm).astype(np.float32)

    def parts_vector(self, parts: list[str]) -> np.ndarray:
        if not parts:
            return self.base_vector()

        part_vectors = np.vstack([self.unit_vector(t) for t in parts])

        vector = part_vectors.mean(axis=0)

        norm = np.linalg.norm(vector)

        if norm == 0.0:
            return self.base_vector()

        return (vector / norm).astype(np.float32)

    def cosine(self, u: np.ndarray, v: np.ndarray) -> float:
        return float(np.dot(u, v))

    def score_candidate(self, candidate_parts: list[str], tail_vector: np.ndarray) -> float:
        # TODO: parametrize
        a = 1.0
        b = 1.0

        candidate_vector = self.parts_vector(candidate_parts)

        alpha_score = self.cosine(candidate_vector, tail_vector)

        beta_score = 0.0

        if len(candidate_parts) > 1:
            for part_left, part_right in zip(candidate_parts, candidate_parts[1:]):
                beta_score += self.cosine(self.unit_vector(part_left), self.unit_vector(part_right))

            beta_score /= (len(candidate_parts) - 1)

        print('candidate:', candidate_parts, 'alpha:', alpha_score, 'beta:', beta_score)

        candidate_score = a * alpha_score + b * beta_score

        return candidate_score

    def choose_candidate_step(self,  # pylint: disable=R0914  # noqa: CCR001
                              tail_parts: list[str],
                              tail_vector: np.ndarray,
                              original_part: str) -> tuple[str, np.ndarray]:
        candidates = self.get_word_forms(original_part)

        print('part candidates for ', original_part, ':', candidates)

        best_candidate = candidates[0]

        first_candidate_parts = [best_candidate] + tail_parts

        best_vector = self.parts_vector(first_candidate_parts)
        best_score = self.score_candidate(first_candidate_parts, tail_vector)

        for candidate in candidates[1:]:
            candidate_parts = [candidate] + tail_parts
            candidate_vector = self.parts_vector(candidate_parts)

            candidate_score = self.score_candidate(candidate_parts, tail_vector)

            if candidate_score > best_score:
                best_candidate = candidate
                best_vector = candidate_vector
                best_score = candidate_score

        return best_candidate, best_vector

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        print('input:', tag.parts)

        tail_parts = [self.get_main_tail_form(tag.parts[-1])]
        tail_vector = self.parts_vector(tail_parts)

        for part in reversed(tag.parts[:-1]):
            best_candidate, tail_vector = self.choose_candidate_step(tail_parts, tail_vector, part)
            tail_parts.insert(0, best_candidate)

        print('output:', tail_parts)
        new_uid = '-'.join(tail_parts)

        if new_uid == tag.uid:
            return True, []

        new_tag = RawTag(
            raw_uid=new_uid,
            normalization=NormalizationMode.raw,
            link=tag.link,
            categories=set(tag.categories),
        )

        return False, [new_tag]
