FROM python:3.10-slim

RUN apt-get update && \
    pip install uv --no-cache-dir && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/

WORKDIR /src/

ADD ./pyproject.toml /src/pyproject.toml
ADD ./README.md /src/README.md

RUN uv pip install --no-cache --system -r pyproject.toml


COPY ./src /src
ENV PYTHONPATH=/src