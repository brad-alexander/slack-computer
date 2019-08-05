#!/usr/bin/env bash
docker run -it --env-file=.env -p80:80 $1