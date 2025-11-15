# Dockerfile for Dora ToolKit with Python and GStreamer
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including GStreamer
RUN apt-get update && apt-get install -y --no-install-recommends \
    # GStreamer core and plugins
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    # Python GObject bindings
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    # Additional tools and libraries
    libcairo2-dev \
    libgirepository1.0-dev \
    pkg-config \
    gcc \
    g++ \
    make \
    cmake \
    git \
    # Network tools (useful for debugging)
    net-tools \
    iproute2 \
    iputils-ping \
    tcpdump \
    # FFmpeg for media processing
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY dtk/ ./dtk/
COPY README.md ./

# Create necessary directories
RUN mkdir -p Resources/cap_store

# Install Python dependencies
# First install PyGObject from apt (already done above), then install package
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ".[streaming]"

# Verify CLI entry point is available
RUN which dora && dora --help

# Set default command to show help
CMD ["dora", "--help"]
