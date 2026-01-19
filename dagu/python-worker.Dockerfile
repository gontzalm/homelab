FROM astral/uv:python3.14-bookworm-slim

RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential python3-dev
RUN rm -rf /var/lib/apt/lists/*
