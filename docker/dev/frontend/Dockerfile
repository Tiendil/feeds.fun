FROM node:lts

RUN apt-get update \
    && apt-get install -y --no-install-recommends codespell \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /repository

COPY ./site/* ./

# in case we copied node_modules from the host
RUN rm -rf node_modules

RUN npm ci

CMD []
