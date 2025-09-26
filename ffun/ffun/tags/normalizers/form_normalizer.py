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

    def _get_word_base_form(self, word: str) -> tuple[str]:
        for upos in ('NOUN', 'VERB', 'ADJ', 'ADV'):
            lemmas = getLemma(word, upos=upos)

            if lemmas:
                return tuple(lemmas)

        return (word,)

    def get_word_base_form(self, word: str) -> tuple[str]:
        if word in self._singular_cache:
            return self._singular_cache[word]

        base_forms = self._get_word_base_form(word)

        self._singular_cache[word] = base_forms

        return base_forms

    def _get_word_plural_form(self, word: str) -> tuple[str]:
        forms = getInflection(word, tag='NNS')

        if forms:
            return tuple(forms)

        return (word,)

    def get_word_plural_form(self, word: str) -> tuple[str]:
        if word in self._plural_cache:
            return self._plural_cache[word]

        plural_form = self._get_word_plural_form(word)

        self._plural_cache[word] = plural_form

        return plural_form

    def get_main_tail_form(self, word: str) -> str:
        base_forms = self.get_word_base_form(word)

        if len(base_forms) == 1:
            return base_forms[0]

        # In case we got smth like axes -> axis, axe, we better keep original word
        # TODO: maybe we can do better, for example, but producing a variant of tag for each base tail

        return (word,)

    def get_word_forms(self, word: str) -> list[str]:
        if len(word) <= 2:
            return [word]

        if any(c.isdigit() for c in word):
            return [word]

        base_form = self.get_word_base_form(word)

        forms = [base_form]

        plural_form = self.get_word_plural_form(base_form)

        if plural_form != base_form:
            forms.append(plural_form)

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

    def choose_candidate_step(self,
                              tail_parts: list[str],
                              tail_vector: np.ndarray,
                              original_part: str) -> tuple[str, np.ndarray]:
        candidates = self.get_word_forms(original_part)

        best_candidate = candidates[0]
        best_vector = self.parts_vector([best_candidate] + tail_parts)
        best_score = self.cosine(best_vector, tail_vector)

        for candidate in candidates[1:]:
            candidate_vector = self.parts_vector([candidate] + tail_parts)

            # TODO: here we may want to add avg_adjacent_cos (pairwise cosine between adjacent parts)
            candidate_score = self.cosine(candidate_vector, tail_vector)

            if candidate_score > best_score:
                best_candidate = candidate
                best_vector = candidate_vector
                best_score = candidate_score

        return best_candidate, best_vector

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        tail_parts = [self.get_main_tail_form(tag.parts[-1])]
        tail_vector = self.parts_vector(tail_parts)

        for part in reversed(tag.parts[:-1]):
            best_candidate, tail_vector = self.choose_candidate_step(tail_parts, tail_vector, part)
            tail_parts.insert(0, best_candidate)

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
