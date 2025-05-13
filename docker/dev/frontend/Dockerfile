FROM node:lts

WORKDIR /repository

COPY ./site/* ./

# in case we copied node_modules from the host
RUN rm -rf node_modules

RUN npm ci

CMD []
