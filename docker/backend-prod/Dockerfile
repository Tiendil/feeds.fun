FROM python:3.11

WORKDIR /

ARG VERSION

RUN pip install ffun==${VERSION}

WORKDIR /ffun

COPY ./yoyo.ini /ffun/yoyo.ini
COPY ./bin /ffun/bin

ENTRYPOINT ["/ffun/bin/entrypoint.sh"]
CMD ["/ffun/bin/run.sh"]
