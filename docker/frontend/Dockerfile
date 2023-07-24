FROM node:lts

WORKDIR /repository

COPY ./site/package*.json ./

RUN npm ci

ENV NODE_PATH /usr/local/lib/node_modules

CMD []
