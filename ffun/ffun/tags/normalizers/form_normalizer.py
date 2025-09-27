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


# TODO: we should periodically trim some caches
class Cache:
    __slots__ = ('_singular_cache', '_plural_cache', '_spacy_data', '_spacy_normal_cache', '_nlp')

    def __init__(self, nlp: spacy.language.Language) -> None:
        self._singular_cache: dict[str, tuple[str]] = {}
        self._plural_cache: dict[str, tuple[str]] = {}

        self._nlp = nlp
        self._spacy_data = nlp.vocab.vectors.data
        self._spacy_normal_cache = np.linalg.norm(self._spacy_data, axis=1)

        # hack to reduce branching (do not check for zero norm each time)
        self._spacy_normal_cache[self._spacy_normal_cache == 0.0] = 1.0

    def get_row_index(self, word: str) -> int:
        # TODO: potential memory leak, since SpaCy inserts each new word into vocab
        key = self._nlp.vocab.strings[word]
        return self._nlp.vocab.vectors.key2row.get(key, -1)

    def get_row_norm(self, index: int) -> float:
        if index < 0:
            return 1.0
        return self._spacy_normal_cache[index]

    def get_row_vector(self, index: int) -> np.ndarray:
        return self._spacy_data[index]

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



# TODO: how could we reuse memory between normalizer runs?
class Solution:
    __slots__ = ('_cache',
                 '_parts',
                 '_alpha',
                 '_beta',
                 '_sum_alpha_score',
                 '_alpha_score',
                 '_sum_beta_score',
                 '_beta_score',
                 '_full_vector',
                 '_score',
                 )

    def __init__(self,
                 cache: Cache,
                 alpha: float = 1.0,
                 beta: float = 1.0
                 ) -> None:
        self._cache = cache
        self._parts = []
        self._alpha = alpha
        self._beta = beta
        self._sum_alpha_score = 0.0
        self._alpha_score = 0.0
        self._sum_beta_score = 0.0
        self._beta_score = 0.0
        self._score = 0.0

    def _cos_rows(self, row_a: int, row_b: int) -> float:
        if row_a < 0 or row_b < 0:
            return 0.0

        vector_a = self._cache.get_row_vector(row_a)
        vector_b = self._cache.get_row_vector(row_b)

        norm_a = self._cache.get_row_norm(row_a)
        norm_b = self._cache.get_row_norm(row_b)

        return float(vector_a @ vector_b) / (norm_a * norm_b)

    def grow(self, part: str) -> 'Solution':
        clone = Solution(cache=self._cache,
                         alpha=self._alpha,
                         beta=self._beta)
        clone._parts = [part] + self._parts

        len_ = len(clone._parts)

        if len_ == 1:
            return clone

        last_index = clone._cache.get_row_index(clone._parts[-1])
        new_index = clone._cache.get_row_index(part)

        if len_ > 1 and new_index >= 0:
            clone._sum_alpha_score += self._sum_alpha_score + clone._cos_rows(new_index, last_index)

        # We have two approaches to treat unknown words (without vectors):
        # 1. Penalize solution with them (current approach):
        #    do not increase sum_(alpha/beta)_score, but increase len_
        #    which decreases average alpha_score
        # 2. Ignore them (calculate average only for known words).
        clone._alpha_score = clone._sum_alpha_score / len_

        if len_ > 2:
            next_index = clone._cache.get_row_index(clone._parts[1])

            if new_index >= 0:
                clone._sum_beta_score += self._sum_beta_score + clone._cos_rows(new_index, next_index)
                clone._beta_score = clone._sum_beta_score / (len_ - 1)

        clone._score = clone._alpha * clone._alpha_score + clone._beta * clone._beta_score

        return clone


# TODO: comment/mark application of each guard
# TODO: maybe organize guards in a lists, if it makes sense
# TODO: tests
# TODO: test performance
# TODO: add to configs
# TODO: add guard for numbers
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

    __slots__ = ('_nlp', '_cache')

    def __init__(self) -> None:
        # TODO: parametrize
        # TODO: when to load model?
        # TODO: do not forget about loading in both dev/prod docker containers
        self._nlp = ensure_model("en_core_web_lg")
        self._cache = Cache(nlp=self._nlp)

    def get_main_tail_form(self, word: str) -> str:
        base_forms = self._cache.get_word_base_forms(word)

        if len(base_forms) == 1:
            return base_forms[0]

        # In case we got smth like axes -> axis, axe, we better keep original word
        # TODO: maybe we can do better, for example, but producing a variant of tag for each base tail
        # print('multiple base forms for tail:', word, '->', base_forms)
        return word

    def get_word_forms(self, word: str) -> list[str]:  # noqa: CCR001
        if len(word) <= 2:
            return [word]

        if any(c.isdigit() for c in word):
            return [word]

        base_forms = self._cache.get_word_base_forms(word)

        # print('!base forms for', word, ':', base_forms)

        forms = list(base_forms)

        for base_form in base_forms:
            for plural_form in self._cache.get_word_plural_forms(base_form):
                # print('!plural form for', base_form, ':', plural_form)
                if plural_form not in forms:
                    forms.append(plural_form)
        # print('!returned forms for', word, ':', forms)
        return forms

    def choose_candidate_step(self,  # pylint: disable=R0914  # noqa: CCR001
                              solution: Solution,
                              original_part: str) -> Solution:
        candidates = self.get_word_forms(original_part)

        if len(candidates) == 1:
            return solution.grow(candidates[0])

        # print('part candidates for ', original_part, ':', candidates)

        best_solution = solution.grow(candidates[0])

        for candidate in candidates[1:]:
            candidate_solution = solution.grow(candidate)

            if candidate_solution._score > best_solution._score:
                best_solution = candidate_solution

        return best_solution

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        # return False, []
        if not tag.uid:
            return False, []

        # print('input:', tag.parts)

        last_part = self.get_main_tail_form(tag.parts[-1])

        # return False, []

        solution = Solution(cache=self._cache).grow(last_part)

        for part in reversed(tag.parts[:-1]):
            solution = self.choose_candidate_step(solution, part)
            # return False, []

        # TODO: iterate over all possible last parts to choose the best

        new_uid = '-'.join(solution._parts)  # TODO: property?

        if new_uid == tag.uid:
            return True, []

        new_tag = RawTag(
            raw_uid=new_uid,
            normalization=NormalizationMode.raw,
            link=tag.link,
            categories=set(tag.categories),
        )

        return False, [new_tag]
