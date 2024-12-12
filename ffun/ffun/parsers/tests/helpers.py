import os
from pathlib import Path

_excluded_suffixes = [".expected.json", "~", "#"]


feeds_fixtures_directory = Path(__file__).parent / "feeds_fixtures"


def feeds_fixtures_names() -> list[str]:
    files = os.listdir(feeds_fixtures_directory)

    return [filename for filename in files if not any(filename.endswith(suffix) for suffix in _excluded_suffixes)]
