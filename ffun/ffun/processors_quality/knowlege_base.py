import pathlib
import toml

from ffun.library.entities import Entry


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
        data = toml.loads(entry_path.read_text())
        return Entry.model_validate(data)

    def get_expected_tags(self, processor: str, id_: int) -> set[str]:
        tags_path = self._dir_tags_expected / processor / f'{id_to_name(id_)}.toml'
        return set(toml.loads(tags_path.read_text())['tags'])

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
