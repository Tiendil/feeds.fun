#!/usr/bin/bash

npm run build-only --prefix ./node_modules/feeds-fun

rm -rf /ffun-static-data/*

cp -r ./node_modules/feeds-fun/dist/* /ffun-static-data/
