#############
# Build stage
#############
FROM node:lts AS builder

WORKDIR /src

COPY site /src/

RUN mv "$(npm pack)" feeds-fun-frontend.tgz

###############
# Install stage
###############

FROM node:lts AS runtime

# We need pandoc to generate the "CRM" pages from markdown
RUN apt-get update && apt-get install -y pandoc

WORKDIR /ffun

COPY --from=builder /src/feeds-fun-frontend.tgz /ffun/

RUN npm install --no-cache ./feeds-fun-frontend.tgz
RUN npm install --no-cache --prefix ./node_modules/feeds-fun

COPY ./docker/prod/frontend/copy-data.sh ./copy-data.sh

CMD ["bash", "./copy-data.sh"]
