#!/usr/bin/bash

FILE=$1

docker compose run --rm -v $FILE:/backup_file postgresql pg_restore -h postgresql -U ffun -d ffun -F t -C /backup_file
