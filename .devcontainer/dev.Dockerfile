FROM nvidia/cuda:12.0.1-runtime-ubuntu20.04

ARG DEBIAN_FRONTEND=noninteractive

# nvidia docker runtime env
ENV NVIDIA_VISIBLE_DEVICES \
        ${NVIDIA_VISIBLE_DEVICES:-all}
ENV NVIDIA_DRIVER_CAPABILITIES \
        ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}graphics,compat32,utility

RUN apt-get update &&\
    apt-get install -y \
        nano git git-lfs \
        build-essential \
        cmake \
        python3 python3-pip \
        ffmpeg

# To ensure QT stuff runs
# From: https://github.com/NVlabs/instant-ngp/discussions/300#discussioncomment-4169112
RUN apt-get install -y '^libxcb.*-dev' libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev

RUN pip3 install --upgrade pip