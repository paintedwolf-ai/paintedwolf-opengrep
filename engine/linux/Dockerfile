# Linux build environment for the downstream Opengrep engine: Ubuntu 24.04 (glibc 2.39,
# which the pinned Linux grammar generator needs), Python 3.13, opam, and the C toolchain
# and libraries the OCaml dependencies need.
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends software-properties-common gnupg ca-certificates \
    && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      python3.13 python3.13-venv python3.13-dev python3 \
      opam build-essential pkg-config m4 unzip bubblewrap rsync patchelf ccache git curl \
      libgmp-dev libev-dev libpcre3-dev libpcre2-dev zlib1g-dev libffi-dev libssl-dev autoconf automake libtool \
    && rm -rf /var/lib/apt/lists/*
# The grammar generator runs each grammar's grammar.js through Node; the version the
# repository's build requires, pinned by nodejs.org's published digest.
ARG NODE_VERSION=26.3.0
ARG NODE_SHA256=0ce210831380ab75a5fec0d3fb6b5af0958898016b2cae51cc2fa11057d2f77e
RUN curl -fsSLo /tmp/node.tar.xz "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - \
    && tar -C /usr/local --strip-components=1 -xJf /tmp/node.tar.xz && rm /tmp/node.tar.xz
ENV OPAMYES=1 OPAMCOLOR=never
WORKDIR /work/src
