# File-to-RTP Streaming with GStreamer

The Dora ToolKit includes GStreamer-based file-to-RTP streaming capabilities for creating ST2110-compliant streams from audio and video files.

## Overview

This feature allows you to:
- Stream audio files as RTP streams (ST2110-30/31 compliant)
- Stream video files as RTP streams (ST2110-20 compliant)
- Support for optional PTP (IEEE 1588) timing synchronization
- Direct network streaming to multicast or unicast addresses
- Optional packet capture for analysis

## Prerequisites

### GStreamer Installation

GStreamer and its Python bindings are required for streaming functionality.

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-rtsp \
    python3-gi \
    gir1.2-gstreamer-1.0
```

**Python Dependencies:**
```bash
pip install -e ".[streaming]"
# Or directly:
pip install PyGObject>=3.42.0
```

**Verify Installation:**
```bash
gst-inspect-1.0 --version
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; print('GStreamer available')"
```

### PTP Support (Optional)

For PTP synchronization, you need a PTP daemon running:

**Install PTP daemon:**
```bash
sudo apt-get install linuxptp
```

**Start PTP daemon:**
```bash
# As PTP slave
sudo ptp4l -i eth0 -s -m

# As PTP master
sudo ptp4l -i eth0 -m
```

## Commands

### Stream Audio File

Stream an audio file as an RTP stream compatible with ST2110-30/31:

```bash
dora media stream-audio <file> --dest-ip <ip> --dest-port <port> [options]
```

**Required Options:**
- `--dest-ip`: Destination IP address (e.g., 239.0.0.1 for multicast)
- `--dest-port`: Destination UDP port

**Audio Options:**
- `--sample-rate`: Sample rate in Hz (default: 48000)
- `--channels`: Number of audio channels (default: 2)
- `--bit-depth`: Bit depth, 16 or 24 (default: 24)

**RTP Options:**
- `--payload-type`: RTP payload type (default: 97 for ST2110-30)
- `--ssrc`: RTP SSRC identifier in hex (e.g., 0x12345678)
- `--packet-time`: Packet time in milliseconds (default: 1ms for ST2110-31)

**Network Options:**
- `-i, --interface`: Network interface to use (e.g., eth0)
- `--src-ip`: Source IP address (optional)

**PTP Options:**
- `--use-ptp`: Enable PTP synchronization
- `--ptp-domain`: PTP domain number (default: 127)

**Capture Options:**
- `--save-pcap`: Save stream to pcap file (requires tcpdump)

---

### Stream Video File

Stream a video file as an RTP stream compatible with ST2110-20:

```bash
dora media stream-video <file> --dest-ip <ip> --dest-port <port> [options]
```

**Required Options:**
- `--dest-ip`: Destination IP address (e.g., 239.0.0.2 for multicast)
- `--dest-port`: Destination UDP port

**Video Options:**
- `--width`: Video width in pixels (default: 1920)
- `--height`: Video height in pixels (default: 1080)
- `--framerate`: Video framerate (default: 30 fps)
- `--pixel-format`: Pixel format - YUY2, UYVY, I420 (default: UYVY for ST2110-20)
- `--interlaced`: Enable interlaced video mode

**RTP Options:**
- `--payload-type`: RTP payload type (default: 96 for ST2110-20)
- `--ssrc`: RTP SSRC identifier in hex (e.g., 0xabcdef00)

**Network Options:**
- `-i, --interface`: Network interface to use (e.g., eth0)
- `--src-ip`: Source IP address (optional)

**PTP Options:**
- `--use-ptp`: Enable PTP synchronization
- `--ptp-domain`: PTP domain number (default: 127)

**Capture Options:**
- `--save-pcap`: Save stream to pcap file (requires tcpdump)

---

## Examples

### Basic Audio Streaming

```bash
# Stream WAV file to multicast group
dora media stream-audio audio.wav --dest-ip 239.0.0.1 --dest-port 5004

# Stream FLAC file with specific parameters
dora media stream-audio audio.flac \
    --dest-ip 239.1.1.1 \
    --dest-port 5004 \
    --sample-rate 48000 \
    --channels 8 \
    --bit-depth 24

# Stream with custom RTP parameters
dora media stream-audio audio.wav \
    --dest-ip 239.0.0.1 \
    --dest-port 5004 \
    --payload-type 97 \
    --ssrc 0x12345678
```

### Basic Video Streaming

```bash
# Stream MP4 file to multicast group
dora media stream-video video.mp4 --dest-ip 239.0.0.2 --dest-port 5005

# Stream 4K video
dora media stream-video video.mov \
    --dest-ip 239.1.1.2 \
    --dest-port 5005 \
    --width 3840 \
    --height 2160 \
    --framerate 60

# Stream interlaced broadcast content
dora media stream-video broadcast.mxf \
    --dest-ip 239.0.0.2 \
    --dest-port 5005 \
    --interlaced \
    --framerate 30
```

### PTP-Synchronized Streaming

```bash
# Audio with PTP synchronization
dora media stream-audio audio.wav \
    --dest-ip 239.0.0.1 \
    --dest-port 5004 \
    --use-ptp \
    --ptp-domain 0 \
    -i eth0

# Video with PTP synchronization
dora media stream-video video.mp4 \
    --dest-ip 239.0.0.2 \
    --dest-port 5005 \
    --use-ptp \
    --ptp-domain 0 \
    -i eth0
```

### Streaming with Packet Capture

When using `--save-pcap`, you'll need to run `tcpdump` in parallel:

**Terminal 1 - Start tcpdump:**
```bash
sudo tcpdump -i eth0 -w audio_stream.pcap udp port 5004
```

**Terminal 2 - Start streaming:**
```bash
dora media stream-audio audio.wav \
    --dest-ip 239.0.0.1 \
    --dest-port 5004 \
    --save-pcap audio_stream.pcap \
    -i eth0
```

The tool will remind you to start tcpdump when `--save-pcap` is used.

### Complete Workflow

1. **Stream audio to network:**
```bash
dora media stream-audio test_audio.wav \
    --dest-ip 239.0.0.1 \
    --dest-port 5004 \
    -i eth0
```

2. **Capture the stream (in another terminal):**
```bash
sudo dora network mcast-join -i eth0 \
    --group 239.0.0.1 \
    --capture 1000 \
    --save captured_stream.pcap
```

3. **Analyze the captured stream:**
```bash
dora media list-streams captured_stream.pcap
```

4. **Export back to audio file:**
```bash
dora media export-audio captured_stream.pcap -o recovered_audio.wav
```

---

## Supported File Formats

GStreamer automatically decodes various formats:

**Audio:**
- WAV (PCM)
- FLAC (lossless)
- MP3 (lossy)
- AAC/M4A
- OGG Vorbis
- AIFF
- And more...

**Video:**
- MP4/MOV (H.264, H.265, etc.)
- AVI
- MKV/WebM
- MXF (broadcast format)
- And more...

The toolkit automatically handles format detection and decoding.

---

## ST2110 Compliance

### Audio (ST2110-30/31)

The audio streaming follows SMPTE ST 2110-30 and ST 2110-31 (AES67) standards:

- **Sample Rates:** 44.1, 48, 88.2, 96 kHz
- **Bit Depths:** 16-bit (L16) or 24-bit (L24)
- **Channels:** 1-16 channels
- **Packet Time:** 1ms (ST2110-31) or configurable
- **RTP Payload:** Type 97 (typical for ST2110-30)

### Video (ST2110-20)

The video streaming follows SMPTE ST 2110-20 for uncompressed video:

- **Resolutions:** 720p, 1080p, 4K UHD, 4K DCI, 8K
- **Frame Rates:** 24, 25, 30, 50, 60 fps (and fractional)
- **Pixel Formats:**
  - UYVY (4:2:2, most common for ST2110-20)
  - YUY2 (4:2:2)
  - I420 (4:2:0)
- **Modes:** Progressive or interlaced
- **RTP Payload:** Type 96 (typical for ST2110-20)

### PTP Timing (IEEE 1588)

When `--use-ptp` is enabled:
- Requires PTP daemon (ptpd/ptp4l) running on the system
- Synchronizes RTP timestamps to PTP clock
- Domain configurable (default: 127)
- Essential for multi-stream lip-sync and frame synchronization

---

## Technical Details

### GStreamer Pipeline Architecture

**Audio Pipeline:**
```
filesrc → decodebin → audioconvert → audioresample →
audio/x-raw → rtpL24pay/rtpL16pay → udpsink
```

**Video Pipeline:**
```
filesrc → decodebin → videoconvert → videoscale →
video/x-raw → rtpvrawpay → udpsink
```

### Best Practices

1. **Network Configuration:**
   - Use multicast addresses (239.0.0.0 - 239.255.255.255)
   - Ensure proper multicast routing
   - Configure firewall to allow UDP ports

2. **Performance:**
   - Use dedicated network interface for streaming
   - Enable jumbo frames for better efficiency
   - Monitor network bandwidth

3. **Synchronization:**
   - Use PTP for multi-stream scenarios
   - Ensure PTP daemon is properly configured
   - Verify PTP synchronization status

4. **Testing:**
   - Test with short files first
   - Verify stream with tcpdump/Wireshark
   - Use `list-streams` to validate RTP stream
   - Export captured stream to verify quality

---

## Troubleshooting

### GStreamer Not Available

**Error:** `GStreamer is not available`

**Solution:**
```bash
# Install GStreamer and plugins
sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-rtsp

# Install Python bindings
sudo apt-get install python3-gi gir1.2-gstreamer-1.0
pip install PyGObject
```

### Missing Plugins

**Error:** `Missing GStreamer plugins`

**Solution:**
```bash
# Install all plugin packages
sudo apt-get install \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly
```

### PTP Not Synchronizing

**Error:** PTP timing not working

**Solutions:**
```bash
# Check PTP daemon status
sudo systemctl status ptp4l

# Verify PTP synchronization
pmc -u -b 0 'GET CURRENT_DATA_SET'

# Check PTP domain
pmc -u -b 0 'GET DEFAULT_DATA_SET'

# Restart PTP daemon
sudo systemctl restart ptp4l
```

### Network Interface Issues

**Error:** Cannot send to multicast address

**Solutions:**
```bash
# Check interface status
ip link show eth0

# Verify multicast routing
ip route show

# Add multicast route if needed
sudo route add -net 239.0.0.0 netmask 255.0.0.0 dev eth0

# Test multicast connectivity
ping 239.0.0.1
```

### File Format Not Supported

**Error:** Cannot decode file

**Solution:**
```bash
# Check what GStreamer can decode
gst-inspect-1.0 | grep -i decoder

# Try to play file with gst-launch-1.0
gst-launch-1.0 filesrc location=file.mp4 ! decodebin ! autovideosink

# Install additional codecs
sudo apt-get install ubuntu-restricted-extras
```

---

## Advanced Usage

### Custom RTP Parameters

```bash
# Specific payload type and SSRC
dora media stream-audio audio.wav \
    --dest-ip 239.0.0.1 \
    --dest-port 5004 \
    --payload-type 100 \
    --ssrc 0xdeadbeef
```

### Multi-Stream Setup

Stream multiple files to different multicast groups:

**Terminal 1 - Audio:**
```bash
dora media stream-audio audio.wav \
    --dest-ip 239.1.1.1 \
    --dest-port 5004 \
    --use-ptp \
    --ptp-domain 0 \
    -i eth0
```

**Terminal 2 - Video:**
```bash
dora media stream-video video.mp4 \
    --dest-ip 239.1.1.2 \
    --dest-port 5005 \
    --use-ptp \
    --ptp-domain 0 \
    -i eth0
```

With PTP enabled, both streams will be synchronized.

### Looping Playback

For continuous streaming, you can use a loop script:

```bash
#!/bin/bash
while true; do
    dora media stream-audio audio.wav \
        --dest-ip 239.0.0.1 \
        --dest-port 5004
done
```

---

## References

- [SMPTE ST 2110-20: Uncompressed Video](https://www.smpte.org/)
- [SMPTE ST 2110-30: PCM Audio](https://www.smpte.org/)
- [SMPTE ST 2110-31: AES67](https://www.smpte.org/)
- [IEEE 1588: Precision Time Protocol](https://standards.ieee.org/standard/1588-2019.html)
- [GStreamer Documentation](https://gstreamer.freedesktop.org/documentation/)
- [RTP: RFC 3550](https://tools.ietf.org/html/rfc3550)
