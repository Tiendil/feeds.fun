import pathlib
import re
import uuid

import frontmatter
import toml

from ffun.core import utils
from ffun.domain.entities import EntryId, SourceId
from ffun.library.entities import Entry
from ffun.processors_quality import errors
from ffun.processors_quality.entities import Attribution, ExpectedTags, ProcessorResult


class FrontmatterTOMLHandler(frontmatter.TOMLHandler):  # type: ignore
    FM_BOUNDARY = re.compile(r"^\-{3,}\s*$", re.MULTILINE)
    START_DELIMITER = END_DELIMITER = "---"


def id_to_name(id_: int) -> str:
    return f"{id_:04d}"


class KnowlegeBase:
    """Interface to operate with the base of test text.

    Catalogs structure:

    ./
    |-- news/
    |   |-- 0001.toml
    |   |-- 0002.toml
    |   |-- ...
    |-- tags-expected/
    |   |-- processor-1/
    |   |   |-- 0001.toml
    |   |   |-- 0002.toml
    |   |   |-- ...
    |-- tags-actual/
    |   |-- processor-1/
    |   |   |-- 0001.toml
    |   |   |-- 0002.toml
    |   |   |-- ...
    |-- tags-last/
    |   |-- processor-1/
    |   |   |-- 0001.toml
    |   |   |-- 0002.toml
    |   |   |-- ...
    """

    __slots__ = ("_dir_root", "_dir_news", "_dir_tags_expected", "_dir_tags_actual", "_dir_tags_last")

    def __init__(self, root: pathlib.Path) -> None:
        self._dir_root = root
        self._dir_news = root / "news"
        self._dir_tags_expected = root / "tags-expected"
        self._dir_tags_actual = root / "tags-actual"
        self._dir_tags_last = root / "tags-last"

    def get_news_entry(self, id_: int) -> Entry:
        entry_path = self._dir_news / f"{id_to_name(id_)}.toml"

        data, body = frontmatter.parse(entry_path.read_text(), handler=FrontmatterTOMLHandler())

        # attribution should be defined for the entry
        try:
            Attribution(**data["attribution"])
        except Exception as e:
            raise errors.AttributionNotDefined(message=str(e)) from e

        return Entry(
            id=EntryId(uuid.UUID(int=0)),
            source_id=SourceId(uuid.UUID(int=0)),
            title=data["title"],
            body=body,
            external_id="",
            external_url=data["external_url"],
            external_tags=data["external_tags"],
            cataloged_at=utils.now(),
            published_at=data["published_at"],
        )

    def get_expected_tags(self, processor: str, id_: int) -> ExpectedTags:
        tags_path = self._dir_tags_expected / processor / f"{id_to_name(id_)}.toml"

        data = toml.loads(tags_path.read_text())

        return ExpectedTags(must_have=set(data["tags_must_have"]), should_have=set(data["tags_should_have"]))

    def get_actual_results(self, processor: str, id_: int) -> ProcessorResult:
        tags_path = self._dir_tags_actual / processor / f"{id_to_name(id_)}.toml"
        return ProcessorResult(**toml.loads(tags_path.read_text()))

    def get_last_results(self, processor: str, id_: int) -> ProcessorResult:
        tags_path = self._dir_tags_last / processor / f"{id_to_name(id_)}.toml"
        return ProcessorResult(**toml.loads(tags_path.read_text()))

    def save_processor_result(self, processor: str, entry_id: int, result: ProcessorResult, actual: bool) -> None:
        (self._dir_tags_last / processor).mkdir(parents=True, exist_ok=True)

        last_path = self._dir_tags_last / processor / f"{id_to_name(entry_id)}.toml"

        content = toml.dumps(result.dict())

        last_path.write_text(content)

        if actual:
            (self._dir_tags_actual / processor).mkdir(parents=True, exist_ok=True)
            actual_path = self._dir_tags_actual / processor / f"{id_to_name(entry_id)}.toml"
            actual_path.write_text(content)

    def save_expected_data(
        self, processor: str, entry_id: int, tags_must_have: set[str], tags_should_have: set[str]
    ) -> None:
        if tags_must_have & tags_should_have:
            raise NotImplementedError("tags_must_have and tags_should_have should not intersect")

        (self._dir_tags_expected / processor).mkdir(parents=True, exist_ok=True)

        tags_path = self._dir_tags_expected / processor / f"{id_to_name(entry_id)}.toml"

        data = {"tags_must_have": list(sorted(tags_must_have)), "tags_should_have": list(sorted(tags_should_have))}

        tags_path.write_text(toml.dumps(data))

    def copy_last_to_actual(self, processor: str, entry_id: int) -> None:
        last_path = self._dir_tags_last / processor / f"{id_to_name(entry_id)}.toml"
        actual_path = self._dir_tags_actual / processor / f"{id_to_name(entry_id)}.toml"

        actual_path.write_text(last_path.read_text())

    def entry_ids(self) -> list[int]:
        return list(sorted(int(entry.stem) for entry in self._dir_news.glob("*.toml")))

    def validate_expected_tags(self) -> None:
        for entry_id in self.entry_ids():
            for processor in self._dir_tags_expected.iterdir():
                self.get_expected_tags(processor.name, entry_id)
