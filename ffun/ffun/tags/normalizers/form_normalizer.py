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

# TODO: update LLM prompt
# TODO: task to generate names for normalized tags according to the statistics of the raw tags?
# TODO: note that it is normalizer, not verboser
# TODO: rewrite all notes, remove alpha mention
# TODO: rename beta to smth better

# TODO: not so good solution, refactor
def ensure_model(name: str,
                 disable=["parser", "ner", "senter", "textcat", "tagger", "lemmatizer"]) -> spacy.language.Language:
    try:
        return spacy.load(name, disable=disable)
    except OSError:
        download(name)
        return spacy.load(name, disable=disable)


# TODO: we should periodically trim word caches
class Cache:
    __slots__ = ('_singular_cache', '_plural_cache', '_forms_cache', '_spacy_data', '_spacy_normal_cache', '_nlp')

    def __init__(self, nlp: spacy.language.Language) -> None:
        self._singular_cache: dict[str, tuple[str]] = {}
        self._plural_cache: dict[str, tuple[str]] = {}
        self._forms_cache: dict[str, tuple[str]] = {}

        self._nlp = nlp
        self._spacy_data = nlp.vocab.vectors.data
        self._spacy_normal_cache = np.linalg.norm(self._spacy_data, axis=1)

        # hack to reduce branching (do not check for zero norm each time)
        self._spacy_normal_cache[self._spacy_normal_cache == 0.0] = 1.0

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
        for upos in ('NOUN', 'VERB', 'ADJ', 'ADV'):
            # TODO: maybe replace with getAllLemmas for optimization
            # TODO: experiment with lemmatize_oov=False
            lemmas = getLemma(word, upos=upos)
            # print(f"upos={upos} lemmas={lemmas}")

            if lemmas:
                return tuple(lemmas)

        return (word,)

    def get_word_base_forms(self, word: str) -> tuple[str]:
        # if word in self._singular_cache:
        #     return self._singular_cache[word]

        if self._fast_word_return(word):
            return (word,)

        base_forms = self._get_word_base_forms(word)

        # for base_form in base_forms:
        #     plural_forms = self.get_word_plural_forms(base_form)
        #     if word in plural_forms:
        #         break
        #         # print(f"word '{word}' not in plural forms of base form '{base_form}': {plural_forms}")
        # else:
        #     return (word,)

        self._singular_cache[word] = base_forms

        return base_forms

    def _get_word_plural_forms(self, word: str) -> tuple[str]:
        # TODO: here we may want to choose proper tag based on which upos produced the base form
        forms = getInflection(word, tag='NNS')

        if forms:
            return tuple(forms)

        return (word,)

    def get_word_plural_forms(self, word: str) -> tuple[str]:
        if word in self._plural_cache:
            return self._plural_cache[word]

        if self._fast_word_return(word):
            return (word,)

        plural_forms = self._get_word_plural_forms(word)

        self._plural_cache[word] = plural_forms

        return plural_forms

    def _get_word_forms(self, word: str) -> tuple[str]:  # noqa: CCR001
        base_forms = self.get_word_base_forms(word)

        forms = list(base_forms)

        for base_form in base_forms:
            for plural_form in self.get_word_plural_forms(base_form):
                if plural_form not in forms:
                    forms.append(plural_form)

        # print(f'CHECK word: {word}, base_forms: {base_forms}, forms: {forms}')
        if word not in forms:
            # print(f"NOT FOUND: word '{word}' base forms: {base_forms}")
            forms.append(word)

        return tuple(forms)

    def get_word_forms(self, word: str) -> tuple[str]:
        if word in self._forms_cache:
            return self._forms_cache[word]

        if self._fast_word_return(word):
            return (word,)

        forms = self._get_word_forms(word)

        self._forms_cache[word] = forms

        return forms


class Solution:
    __slots__ = ('_cache',
                 'parts',
                 '_beta',
                 '_sum_beta_score',
                 '_beta_score',
                 'score',
                 )

    def __init__(self,
                 cache: Cache,
                 beta: float = 1.0
                 ) -> None:
        self._cache = cache
        self.parts = ()
        self._beta = beta
        self._sum_beta_score = 0.0
        self._beta_score = 0.0
        self.score = 0.0

    def _cos_rows(self, row_a: int, row_b: int, default: np.float32 = np.float32(0.0)) -> np.float32:
        if row_a < 0 or row_b < 0:
            return default

        vector_a = self._cache.get_row_vector(row_a)
        vector_b = self._cache.get_row_vector(row_b)

        norm_a = self._cache.get_row_norm(row_a)
        norm_b = self._cache.get_row_norm(row_b)

        return (vector_a @ vector_b) / (norm_a * norm_b)

    def sync_score(self) -> None:
        self._beta_score = self._sum_beta_score / (len(self.parts) - 1) if len(self.parts) > 1 else 0.0
        self.score = self._beta * self._beta_score

    ########################################
    # We choose the best solution by comparing their scores.
    # The score consists of two parts:
    #
    # 1. Alpha score: average cosine distance bestween each part and the last one (it is our anchor)
    # 2. Beta score: average cosine distance between each two adjacent parts
    #
    # The final score is a weighted sum of these two scores.
    #
    # We receive the final solution by growing the best one from its last part to the first one.
    # That allows us to go away from checking cortesian product of all possible combinations of parts.
    #
    # This solution is a compromise between performance and quality.
    #
    # In the future we may want to improve it by using more advanced approaches:
    # - Use original text vector as the anchor instead of the last part of the tag
    # - Check every possible combination of parts against the original text vector
    ########################################
    def grow(self, part: str) -> 'Solution':
        clone = Solution(cache=self._cache,
                         beta=self._beta)
        clone.parts = (part,) + self.parts

        len_ = len(clone.parts)

        if len_ == 1:
            return clone

        new_index = clone._cache.get_row_index(part)

        # We have two approaches to treat unknown words (without vectors):
        # 1. Penalize solution with them (current approach):
        #    do not increase sum_(alpha/beta)_score, but increase len_
        #    which decreases average alpha_score
        # 2. Ignore them (calculate average only for known words).
        if len_ > 1 and new_index >= 0:
            # TODO: what if next_index is unknown?
            next_index = clone._cache.get_row_index(clone.parts[1])
            clone._sum_beta_score = self._sum_beta_score + clone._cos_rows(new_index, next_index)

        clone.sync_score()

        return clone

    def replace_tail(self, part: str) -> 'Solution':
        clone = Solution(cache=self._cache,
                         beta=self._beta)

        clone.parts = self.parts[:-1] + (part,)

        len_ = len(clone.parts)

        if len_ == 1:
            # TODO: what to do in that case? how to compute tags?
            return clone

        # TODO: what if on of last_index < 0
        original_last_index = clone._cache.get_row_index(self.parts[-1])
        new_last_index = clone._cache.get_row_index(part)

        if len_ > 1:
            prev_index = clone._cache.get_row_index(clone.parts[-2])
            old_beta_score = clone._cos_rows(original_last_index, prev_index)
            new_beta_score = clone._cos_rows(new_last_index, prev_index)
            clone._sum_beta_score = self._sum_beta_score - old_beta_score + new_beta_score

        clone.sync_score()

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

    __slots__ = ('_nlp', '_cache')

    def __init__(self) -> None:
        # TODO: parametrize
        # TODO: when to load model?
        # TODO: do not forget about loading in both dev/prod docker containers
        # TODO: ensure we load the model in memory only on its first use, not on code initialization
        self._nlp = ensure_model("en_core_web_lg")
        self._cache = Cache(nlp=self._nlp)

    def get_main_tail_form(self, word: str) -> str:
        base_forms = self._cache.get_word_base_forms(word)

        # print(f"word '{word}' base forms: {base_forms}")

        if len(base_forms) == 1:
            return base_forms[0]

        # In case we got smth like axes -> axis, axe, we better keep original word
        # See the comment .normalize(...) method for details
        return word

    def grow_candidate(self,  # pylint: disable=R0914  # noqa: CCR001
                       solution: Solution,
                       original_part: str) -> Solution:
        candidates = self._cache.get_word_forms(original_part)

        if len(candidates) == 1:
            return solution.grow(candidates[0])

        best_solution = solution.grow(candidates[0])

        for candidate in candidates[1:]:
            candidate_solution = solution.grow(candidate)

            if candidate_solution.score > best_solution.score:
                best_solution = candidate_solution

        return best_solution

    def choose_best_tail(self,
                         solution: Solution,
                         last_parts: tuple[str]) -> Solution:
        if len(last_parts) == 1:
            return solution

        best_solution = solution

        for last_part in last_parts:
            if last_part == solution.parts[-1]:
                continue

            candidate_solution = solution.replace_tail(last_part)

            if candidate_solution.score > best_solution.score:
                best_solution = candidate_solution

        return best_solution

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        canonical_part = tag.parts[-1]

        # print(f"canonical part: {canonical_part}")
        # print(f"candidates: {self._cache.get_word_forms(canonical_part)}")

        solutions = [Solution(cache=self._cache).grow(part)
                     for part in self._cache.get_word_forms(canonical_part)]

        for part in reversed(tag.parts[:-1]):
            new_solutions = []

            for solution in solutions:
                new_solutions.append(self.grow_candidate(solution, part))

            solutions = new_solutions

        solutions.sort(key=lambda s: s.score, reverse=True)

        print('scores')
        for solution in solutions:
            print(f"  {solution.parts} -> {solution.score}")

        best_solution = solutions[0]

        # At this point we have the best tag for the fixed last part
        # But in some case we can not normalize the last part properly
        # For example, multiple words can have single plural form: `axes` <- `axis`, `axe`
        # so we can not choose the best last part at the first step, and use the original one
        # But now we can freeze the beginning of the tag and re-run the algorithm changing the last part
        # So we choose the best last part for the already correct chosen beginning of the tag

        # TODO: optimize to not call if there were only single option
        # last_parts = self._cache.get_word_forms(canonical_part)
        # last_parts = self._cache.get_word_forms(last_part)
        # last_parts = self._cache.get_word_base_forms(last_part)

        # print(f"original part: {tag.parts[-1]}")
        # print(f"last part: {last_part}")
        # print(f"last parts: {last_parts}")

        # solution = self.choose_best_tail(solution, last_parts)

        new_uid = '-'.join(best_solution.parts)

        if new_uid == tag.uid:
            return True, []

        new_tag = RawTag(
            raw_uid=new_uid,
            normalization=NormalizationMode.raw,
            link=tag.link,
            categories=set(tag.categories),
        )

        return False, [new_tag]
