FROM astral/uv:trixie

# Install build deps
RUN apt update
RUN apt install -y --no-install-recommends build-essential python3-dev curl
RUN rm -rf /var/lib/apt/lists/*
