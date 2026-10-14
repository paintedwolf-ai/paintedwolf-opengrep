# Prepare environment for Linux engines: the source checkout, patches, and grammar
# generation, whose pinned generator needs glibc 2.39. Release builds prepare on the
# hosted Ubuntu 24.04 runner itself; this image reproduces that locally.
FROM ubuntu:24.04@sha256:008173c23f95b170204355c12626cb5a965d779a7e1283b09e9cffbb1bf33ca3
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates curl git xz-utils python3 libatomic1 \
    && rm -rf /var/lib/apt/lists/*
# The generator runs each grammar's grammar.js through Node, pinned by nodejs.org's
# digest for the image's architecture (TARGETARCH is amd64 or arm64).
ARG TARGETARCH
ARG NODE_VERSION=26.3.0
ARG NODE_SHA256_AMD64=0ce210831380ab75a5fec0d3fb6b5af0958898016b2cae51cc2fa11057d2f77e
ARG NODE_SHA256_ARM64=392f291d00c74644f35ec0325cd03d9d4f5a627c926213fbd05167c0cba9f977
RUN case "${TARGETARCH}" in \
      amd64) NODE_ARCH=x64; NODE_SHA256="${NODE_SHA256_AMD64}" ;; \
      arm64) NODE_ARCH=arm64; NODE_SHA256="${NODE_SHA256_ARM64}" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl -fsSLo /tmp/node.tar.xz "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - \
    && tar -C /usr/local --strip-components=1 -xJf /tmp/node.tar.xz && rm /tmp/node.tar.xz
WORKDIR /work/src
