import typer

from ffun.cli.commands import cleaner  # noqa: F401
from ffun.cli.commands import experiments  # noqa: F401
from ffun.cli.commands import metrics  # noqa: F401
from ffun.cli.commands import processors_quality  # noqa: F401
from ffun.cli.commands import profile  # noqa: F401
from ffun.cli.commands import user_settings  # noqa: F401
from ffun.core import logging

app = typer.Typer()

logger = logging.get_module_logger()


app.add_typer(processors_quality.cli_app, name="processors-quality")
app.add_typer(user_settings.cli_app, name="user-settings")
app.add_typer(cleaner.cli_app, name="cleaner")
app.add_typer(metrics.cli_app, name="metrics")
app.add_typer(profile.cli_app, name="profile")
app.add_typer(experiments.cli_app, name="experiments")


if __name__ == "__main__":
    app()
