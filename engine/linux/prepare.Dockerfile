# Prepare environment for Linux engines: the source checkout, patches, and grammar
# generation, whose pinned generator needs glibc 2.39. Release builds prepare on the
# hosted Ubuntu 24.04 runner itself; this image reproduces that locally.
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates curl git xz-utils python3 libatomic1 \
    && rm -rf /var/lib/apt/lists/*
# The generator runs each grammar's grammar.js through Node, pinned by nodejs.org's digest.
ARG NODE_VERSION=26.3.0
ARG NODE_SHA256=0ce210831380ab75a5fec0d3fb6b5af0958898016b2cae51cc2fa11057d2f77e
RUN curl -fsSLo /tmp/node.tar.xz "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - \
    && tar -C /usr/local --strip-components=1 -xJf /tmp/node.tar.xz && rm /tmp/node.tar.xz
WORKDIR /work/src
