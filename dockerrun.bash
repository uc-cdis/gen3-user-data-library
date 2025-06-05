#!/bin/bash

nginx
poetry run gunicorn gen3userdatalibrary.main:app_instance -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py --user gen3 --group gen3
