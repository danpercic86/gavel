FROM python:3.10-slim

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

RUN set -ex

# Set the time zone inside the container
RUN apt install tzdata \
    && cp /usr/share/zoneinfo/Europe/Bucharest /etc/localtime \
    && echo "Europe/Bucharest" > /etc/timezone

COPY poetry.lock pyproject.toml ./

RUN rm /bin/sh && ln -s /bin/bash /bin/sh

RUN apt update

RUN apt -y install curl

RUN apt -y install graphviz

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

# some packages need to be compiled from source and have build-time dependencies
RUN apt -y install gcc libpq-dev \
    && source ${HOME}/.poetry/env \
    && pip install --upgrade pip \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi \
    && pip install gunicorn whitenoise Redis

# link image with github repo
LABEL org.opencontainers.image.source=https://github.com/BanatIT/gavel

EXPOSE 80

ENV PORT=80

CMD ["sh", "-c", "python initialize.py && gunicorn -b :${PORT} -w 3 gavel:app"]

COPY . .
