# Docker Build Issues - Work in Progress

## Problem Summary
Attempting to build a Docker image for Dora ToolKit with GStreamer support. The build is failing with girepository-2.0 not found errors when trying to install Python dependencies with PyGObject.

## Current State

### Branch
Working on: `claude/fix-gstreamer-dependencies-01FNDMUNmKEcDcpxwr8ZeKNJ`

### What We've Tried

1. **Initial Dockerfile from `claude/fix-uv-docker-build-01VBjKyJq3rixWU4TxGJxntw`**
   - Basic Ubuntu 24.04 base
   - uv for Python package management
   - Minimal GStreamer packages

2. **Added Complete GStreamer Dependencies** (current Dockerfile)
   - Based on working reference from another project
   - Includes all GStreamer plugins and platform integrations
   - Added development packages: `gstreamer1.0-dev`, `libgstreamer-plugins-base1.0-dev`
   - Added Python bindings: `python3-gi`, `python3-gi-cairo`, `python-gi-dev`
   - Added introspection: `libgirepository1.0-dev`, `gobject-introspection`
   - Still failing with girepository-2.0 errors

## Known Issues

### girepository-2.0 vs girepository-1.0
The error suggests that PyGObject or some dependency is looking for girepository-2.0, but:
- Ubuntu 24.04 may only have girepository-1.0 packages available
- The `libgirepository1.0-dev` package provides GIRepository-2.0.pc on Ubuntu 24.04, but there might be a version mismatch
- PyGObject version in pyproject.toml might be too new for the system packages

## Next Steps to Investigate

1. **Check PyGObject version compatibility**
   - Look at `pyproject.toml` to see which PyGObject version is specified
   - Try pinning to an older PyGObject version compatible with Ubuntu 24.04's girepository
   - Consider PyGObject 3.42.x or 3.44.x instead of latest

2. **Try different base images**
   - Consider Ubuntu 22.04 (jammy) instead of 24.04
   - Try Debian bookworm or bullseye
   - Try Fedora/CentOS which might have better GStreamer support

3. **Use system PyGObject instead of building**
   - Install `python3-gi` from apt and exclude PyGObject from uv sync
   - May need to adjust pyproject.toml dependencies

4. **Debug the actual error**
   - Run `docker build` to see the full error message
   - Check if it's a pkg-config path issue
   - Verify what version of girepository is actually available in the container

5. **Check pkg-config**
   - The build might not be finding the .pc files
   - May need to set PKG_CONFIG_PATH environment variable
   - Run `pkg-config --list-all | grep gi` in container to verify

## Reference Working Dockerfile
The working GStreamer Dockerfile from another project uses:
```dockerfile
RUN apt-get -y --no-install-recommends install \
    gstreamer1.0-tools \
    gstreamer1.0-dev \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-* \
    libgstreamer-plugins-base1.0-dev \
    libgirepository1.0-dev \
    python3-gi \
    python-gi-dev \
    # ... etc
```

But their build environment and Python dependencies might be different.

## Files Modified
- `Dockerfile` - Main Docker build configuration
- `.dockerignore` - Exclude unnecessary files from Docker context
- `DOCKER.md` - Usage documentation

## Commands to Resume Work

```bash
# Check out the branch
git checkout claude/fix-gstreamer-dependencies-01FNDMUNmKEcDcpxwr8ZeKNJ

# Try building to see current error
docker build -t dora-toolkit:latest .

# Debug inside a container
docker run -it ubuntu:24.04 /bin/bash
# Then manually install packages and check pkg-config

# Check pyproject.toml for PyGObject version
cat pyproject.toml | grep -A5 PyGObject
```

## Notes
- The uv package manager is working correctly
- Python 3.12 installation is working
- The issue is specifically with GObject Introspection / girepository during Python package installation
- This is a common issue when building PyGObject from source in containers
