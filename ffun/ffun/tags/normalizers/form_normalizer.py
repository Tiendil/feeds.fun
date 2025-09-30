import functools

import numpy as np
import spacy
from lemminflect import getAllLemmas, getAllLemmasOOV, getInflection

from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


class Cache:
    __slots__ = ("_spacy_data", "_spacy_normal_cache", "_nlp", "_cached_cos_rows", "_cached_get_word_forms")

    def __init__(self, model: str, cos_cache_size: int, forms_cache_size: int):
        self._nlp = spacy.load(model, disable=["parser", "ner", "senter", "textcat", "tagger", "lemmatizer"])
        self._spacy_data = self._nlp.vocab.vectors.data
        self._spacy_normal_cache = np.linalg.norm(self._spacy_data, axis=1)

        # hack to reduce branching (do not check for zero norm each time)
        self._spacy_normal_cache[self._spacy_normal_cache == 0.0] = 1.0

        self._cached_get_word_forms = functools.lru_cache(maxsize=forms_cache_size)(self._raw_get_word_forms)
        self._cached_cos_rows = functools.lru_cache(maxsize=cos_cache_size)(self._raw_cos_rows)

    def get_row_index(self, word: str) -> int:
        # vocab.strings is a hash table => we may see a memory growth here
        key = self._nlp.vocab.strings[word]
        return self._nlp.vocab.vectors.key2row.get(key, -1)

    def get_row_norm(self, index: int, default: np.float32 = np.float32(1.0)) -> np.float32:
        if index < 0:
            # the same hack as in __init__
            return default
        return self._spacy_normal_cache[index]

    def get_row_vector(self, index: int) -> np.ndarray:
        return self._spacy_data[index]

    def _fast_word_return(self, word: str) -> bool:
        if len(word) <= 2:
            return True

        if any(c.isdigit() for c in word):
            return True

        return False

    def _get_word_base_forms(self, word: str) -> tuple[str]:
        # getLemma calls getAllLemmas and then filters results by `upos`
        # => we use getAllLemmas directly to speed up things

        lemmas = getAllLemmas(word)

        for upos in ("NOUN", "VERB", "ADJ", "ADV"):
            if upos in lemmas:
                return tuple(lemmas[upos])

            lemmas_oov = getAllLemmasOOV(word, upos=upos)

            if upos in lemmas_oov:
                return tuple(lemmas_oov[upos])

        return (word,)

    def _get_word_plural_forms(self, word: str) -> tuple[str]:
        # Shoud return plural form if it is possible, else []
        forms = getInflection(word, tag="NNS")

        if forms:
            return tuple(forms)

        return (word,)

    def _raw_get_word_forms(self, word: str) -> tuple[str]:  # noqa: CCR001
        base_forms = self._get_word_base_forms(word)

        forms = list(base_forms)

        for base_form in base_forms:
            for plural_form in self._get_word_plural_forms(base_form):
                if plural_form not in forms:
                    forms.append(plural_form)

        if word not in forms:
            forms.append(word)

        return tuple(forms)

    def get_word_forms(self, word: str) -> tuple[str]:
        if self._fast_word_return(word):
            return (word,)

        return self._cached_get_word_forms(word)

    def _raw_cos_rows(self, row_a: int, row_b: int) -> np.float32:
        vector_a = self.get_row_vector(row_a)
        vector_b = self.get_row_vector(row_b)

        norm_a = self.get_row_norm(row_a)
        norm_b = self.get_row_norm(row_b)

        return (vector_a @ vector_b) / (norm_a * norm_b)

    def cos_rows(self, row_a: int, row_b: int, default: np.float32 = np.float32(0.0)) -> np.float32:
        if row_a < 0 or row_b < 0:
            return default

        # optimize caching
        if row_a > row_b:
            row_a, row_b = row_b, row_a

        return self._cached_cos_rows(row_a, row_b)


########################################
# We choose the best solution by comparing their scores.
# The score is the sum of cosine distances between neighboring parts of the tag.
#
# We receive the list of final solutions by:
#
# - starting from the last part of the tag — one solution per each of its word forms;
# - for each next part of the tag we choose the best word form by comparing scores of all possible solutions.
#
# That allows us to go away from checking cortesian product of all possible combinations of parts.
#
# In the future we may want to improve it by using more advanced approaches:
#
# - Use original text vector as the anchor to calculate cosine with the whole tag candidate (not with parts)
# - Collect frequency statistics of raw tags produced by LLMs and use the most frequent ones as target tags
#   to normalize to
########################################
class Solution:
    __slots__ = (
        "_cache",
        "parts",
        "score",
    )

    def __init__(
        self,
        cache: Cache,
    ) -> None:
        self._cache = cache
        self.parts = ()
        self.score = 0.0

    def total_characters(self) -> int:
        return sum(len(part) for part in self.parts)

    def grow(self, part: str) -> "Solution":
        clone = Solution(cache=self._cache)
        clone.parts = (part,) + self.parts

        len_ = len(clone.parts)

        if len_ == 1:
            # Theoretically, here we can calculate cos between the topmost right part of the tag
            # and some "anchort word" like "tag" to get some score for single-word tags
            # But, due to:
            # - how SpaCy works (word vectors are not so meaningful, as we want them to be)
            # - we have "smart" sorting of final solutions
            # - this change does not affect the quality of normalization significantly
            # => we may skip it for now
            return clone

        new_index = clone._cache.get_row_index(part)

        if len_ > 1 and new_index >= 0:
            # TODO: what if next_index is unknown?
            next_index = clone._cache.get_row_index(clone.parts[1])
            clone.score = self.score + clone._cache.cos_rows(new_index, next_index)

        return clone


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

    __slots__ = ("_nlp", "_cache", "_spacy_model", "_cos_cache_size", "_forms_cache_size")

    def __init__(
        self, model: str = "en_core_web_lg", cos_cache_size: int = 100_000, forms_cache_size: int = 100_000
    ) -> None:
        self._spacy_model = model
        self._cos_cache_size = cos_cache_size
        self._forms_cache_size = forms_cache_size
        self._cache: Cache | None = None

    # Cache loads Spacy model, so we initialize it lazily
    def cache(self) -> Cache:
        if self._cache is None:
            self._cache = Cache(
                model=self._spacy_model, cos_cache_size=self._cos_cache_size, forms_cache_size=self._forms_cache_size
            )
        return self._cache

    def grow_candidate(
        self, solution: Solution, original_part: str  # pylint: disable=R0914  # noqa: CCR001
    ) -> Solution:
        candidates = self.cache().get_word_forms(original_part)

        if len(candidates) == 1:
            return solution.grow(candidates[0])

        best_solution = solution.grow(candidates[0])

        for candidate in candidates[1:]:
            candidate_solution = solution.grow(candidate)

            if candidate_solution.score > best_solution.score:
                best_solution = candidate_solution

        return best_solution

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        canonical_part = tag.parts[-1]

        solutions = [Solution(cache=self.cache()).grow(part) for part in self.cache().get_word_forms(canonical_part)]

        for part in reversed(tag.parts[:-1]):
            new_solutions = []

            for solution in solutions:
                new_solutions.append(self.grow_candidate(solution, part))

            solutions = new_solutions

        # We prefare
        # - the solution with higher score
        # - the solution with less characters if scores are equal
        # - fixed alphabetical order if both score and length are equal
        solutions.sort(key=lambda s: (s.score, -s.total_characters(), s.parts), reverse=True)

        best_solution = solutions[0]

        new_uid = "-".join(best_solution.parts)

        if new_uid == tag.uid:
            return True, []

        # TODO: mark tags, produced by normalizer, to skip them on the second iteration
        #       but remember, that not every normalizer expect such logic, some want to process
        #       tags in chain
        # TODO: we may want to cach in domain.py chain of tags, to skip the whole normalizers operations
        new_tag = RawTag(
            raw_uid=new_uid,
            normalization=NormalizationMode.raw,
            link=tag.link,
            categories=set(tag.categories),
        )

        return False, [new_tag]
