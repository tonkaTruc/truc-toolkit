# Dockerfile for Dora ToolKit with Python and GStreamer
# Using Ubuntu 24.04 for GObject Introspection with girepository-2.0 support
FROM ubuntu:24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install Python and system dependencies including GStreamer
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    # Build tools
    curl \
    git \
    cmake \
    autoconf \
    automake \
    libtool \
    pkg-config \
    gcc \
    g++ \
    make \
    # GStreamer core and development libraries
    gstreamer1.0-tools \
    gstreamer1.0-dev \
    libgstreamer1.0-0 \
    # GStreamer plugins
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    # GStreamer platform integrations
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    # GStreamer development libraries
    libgstreamer-plugins-base1.0-dev \
    # GObject Introspection and Python bindings
    libgirepository1.0-dev \
    gobject-introspection \
    libglib2.0-dev \
    gir1.2-gstreamer-1.0 \
    python3-gi \
    python3-gi-cairo \
    python-gi-dev \
    # Cairo for graphics
    libcairo2-dev \
    # Network tools (useful for debugging)
    net-tools \
    iproute2 \
    iputils-ping \
    tcpdump \
    # FFmpeg for media processing
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    # Set python3.12 as default python3
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY dtk/ ./dtk/
COPY README.md ./

# Create necessary directories
RUN mkdir -p Resources/cap_store

# Install Python dependencies using uv
RUN uv sync --extra streaming

# Add uv's virtual environment to PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Verify CLI entry point is available
RUN which dora && dora --help

# Set default command to show help
CMD ["dora", "--help"]
