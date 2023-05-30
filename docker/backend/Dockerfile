FROM python:3.11

WORKDIR /repository

RUN pip install poetry

# copied code will be replaced by mounted volume in docker-compose
# but we need to copy it to install cli utils from pyproject.toml
COPY ./ffun ./

RUN poetry install --no-interaction --no-ansi

CMD []
