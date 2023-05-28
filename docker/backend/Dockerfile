FROM python:3.11

WORKDIR /repository

RUN pip install poetry

COPY ./ffun/pyproject.toml ./ffun/poetry.lock* ./

RUN poetry install --no-interaction --no-ansi

CMD []
