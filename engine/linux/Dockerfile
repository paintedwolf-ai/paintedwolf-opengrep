# Compile environment for Linux engines: Ubuntu 22.04, whose glibc 2.35 is the
# release baseline, with opam, the C toolchain, and the headers CPython's modules
# build against. CPython itself comes from its pinned source (locks/runtimes.json).
FROM ubuntu:22.04@sha256:b8b6ee6aa931ecd9d0d952abc34dc0e5f7c6a30c6bb71b079fe399fde0329c02
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      ca-certificates curl git xz-utils python3 opam build-essential pkg-config m4 unzip bubblewrap rsync patchelf \
      autoconf automake libtool libssl-dev libffi-dev libbz2-dev liblzma-dev libsqlite3-dev uuid-dev zlib1g-dev \
      libgmp-dev libev-dev libpcre3-dev libpcre2-dev \
    && rm -rf /var/lib/apt/lists/*
ENV OPAMYES=1 OPAMCOLOR=never
WORKDIR /work/src
