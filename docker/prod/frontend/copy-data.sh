#!/usr/bin/bash

npm run build-only --prefix ./node_modules/feeds-fun

cp -r ./node_modules/feeds-fun/dist /ffun-static-data
