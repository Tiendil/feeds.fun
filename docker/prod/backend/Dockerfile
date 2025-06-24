#############
# Build stage
#############
FROM python:3.13 AS builder

WORKDIR /src

RUN pip install poetry

COPY ffun /src/

RUN poetry build --format wheel

###############
# Install stage
###############

FROM python:3.13 AS runtime

WORKDIR /ffun

COPY --from=builder /src/dist/*.whl /ffun/

RUN pip install --no-cache /ffun/*.whl && rm /ffun/*.whl

CMD ["ffun"]
