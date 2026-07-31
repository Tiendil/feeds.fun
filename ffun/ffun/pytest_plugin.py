import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("ffun")
    group.addoption(
        "--detect-async-leaks",
        action="store_true",
        default=False,
        help="Detect leaked asyncio tasks and event-loop blocking.",
    )
