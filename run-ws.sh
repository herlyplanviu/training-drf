#!/bin/bash
export DJANGO_SETTINGS_MODULE=core.settings
uvicorn core.asgi:application --reload --port 8080
