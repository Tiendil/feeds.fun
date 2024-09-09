#!/usr/bin/bash

docker compose run --rm postgresql pg_dump -h postgresql -U ffun -F c -W ffun
