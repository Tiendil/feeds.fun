#!/usr/bin/bash

FILE=$1

docker compose run --rm -v $FILE:/backup_file postgresql pg_restore -h postgresql -U root -d ffun -F c -C /backup_file
