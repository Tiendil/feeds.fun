import pathlib
import toml
import re
import uuid

from ffun.core import utils
from ffun.library.entities import Entry
from ffun.processors_quality.entities import ExpectedTags
import frontmatter


class FrontmatterTOMLHandler(frontmatter.TOMLHandler):
    FM_BOUNDARY = re.compile(r"^\-{3,}\s*$", re.MULTILINE)
    START_DELIMITER = END_DELIMITER = "---"


def id_to_name(id_: int) -> str:
    return f'{id_:04d}'


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

    __slots__ = ('_dir_root', '_dir_news', '_dir_tags_expected', '_dir_tags_actual', '_dir_tags_last')

    def __init__(self, root: pathlib.Path) -> None:
        self._dir_root = root
        self._dir_news = root / 'news'
        self._dir_tags_expected = root / 'tags-expected'
        self._dir_tags_actual = root / 'tags-actual'
        self._dir_tags_last = root / 'tags-last'

    def get_news_entry(self, id_: int) -> Entry:
        entry_path = self._dir_news / f'{id_to_name(id_)}.toml'

        data, body = frontmatter.parse(entry_path.read_text(), handler=FrontmatterTOMLHandler())

        return Entry(id=uuid.UUID(int=0),
                     feed_id=uuid.UUID(int=0),
                     title=data['title'],
                     body=body,
                     external_id='',
                     external_url=data['external_url'],
                     external_tags=data['external_tags'],
                     cataloged_at=utils.now(),
                     published_at=data['published_at'])

    def get_expected_tags(self, processor: str, id_: int) -> ExpectedTags:
        tags_path = self._dir_tags_expected / processor / f'{id_to_name(id_)}.toml'

        data = toml.loads(tags_path.read_text())

        return ExpectedTags(must_have=set(data['tags_must_have']),
                            should_have=set(data['tags_should_have']))

    def get_actual_tags(self, processor: str, id_: int) -> set[str]:
        tags_path = self._dir_tags_actual / processor / f'{id_to_name(id_)}.toml'
        return set(toml.loads(tags_path.read_text())['tags'])

    def get_last_tags(self, processor: str, id_: int) -> set[str]:
        tags_path = self._dir_tags_last / processor / f'{id_to_name(id_)}.toml'
        return set(toml.loads(tags_path.read_text())['tags'])

    def save_actual_tags(self, processor: str, id_: int, tags: set[str]) -> None:
        tags_path = self._dir_tags_actual / processor / f'{id_to_name(id_)}.toml'
        tags_path.write_text(toml.dumps({'tags': list(tags)}))

    def save_last_tags(self, processor: str, id_: int, tags: set[str]) -> None:
        tags_path = self._dir_tags_last / processor / f'{id_to_name(id_)}.toml'
        tags_path.write_text(toml.dumps({'tags': list(tags)}))
