FROM node:lts

WORKDIR /repository

COPY ./site/package*.json ./

ENV NODE_PATH /usr/local/lib/node_modules

RUN npm ci

CMD []
