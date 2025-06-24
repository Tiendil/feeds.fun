FROM python:3.13

RUN pip install poetry

ARG UID=1000
ARG GID=1000
ARG USER=ffun

RUN groupadd --gid $GID $USER && useradd --create-home --uid $UID --gid $USER --shell /bin/bash $USER

USER $USER

WORKDIR /repository

# copied code will be replaced by mounted volume in docker-compose
# but we need to copy it to install cli utils from pyproject.toml
COPY ./ffun ./

RUN poetry install --no-interaction --no-ansi

USER $USER
CMD []
