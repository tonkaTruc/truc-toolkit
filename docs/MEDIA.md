# SMPTE ST 2110 Media Processing

The Dora ToolKit includes comprehensive support for extracting and exporting media from SMPTE ST 2110 packet captures. This document describes the media processing capabilities and how to use them.

## Overview

SMPTE ST 2110 is a suite of standards for professional media transport over IP networks. The toolkit supports:

- **ST 2110-20**: Uncompressed video
- **ST 2110-30**: Uncompressed PCM audio
- **ST 2110-40**: Ancillary data (captions, timecode, metadata)

## Prerequisites

### Required Dependencies

The media processing features require additional Python packages:

```bash
pip install numpy soundfile ffmpeg-python pillow
```

###FFmpeg

Video export requires FFmpeg to be installed on your system:

- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **CentOS/RHEL**: `sudo yum install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## Commands

### List RTP Streams

Analyze a pcap file and list all detected RTP streams:

```bash
dtk media list-streams <pcap_file> [--use-ptp]
```

**Options:**
- `--use-ptp`: Extract and display PTP timing information

**Example:**
```bash
dtk media list-streams ST2110-30_audio.pcap
dtk media list-streams video_capture.pcap --use-ptp
```

**Output:**
```
Found 2 RTP stream(s):

SSRC: 0x12345678
  Payload Type: 97 (ST2110-30 Audio)
  Packets: 1000
  Sequence: 0 -> 999
  Timestamp Range: 0 -> 48000
  Duration: 1.000s
  Packets Lost: 0 (0.00%)
  Out of Order: 0
```

---

### Export Audio (ST 2110-30)

Export audio streams from pcap to various audio formats:

```bash
dtk media export-audio <pcap_file> -o <output_file> [options]
```

**Options:**
- `-o, --output`: Output file path (required)
- `-f, --format`: Output format: `wav` (default), `flac`, or `mp3`
- `--ssrc`: Specific SSRC to export (hex, e.g., `0x12345678`)
- `--sample-rate`: Sample rate in Hz (auto-detect if not specified)
- `--bit-depth`: Bit depth for output: `16` or `24` (auto-detect if not specified)
- `--channels`: Number of audio channels (auto-detect if not specified)
- `--use-ptp`: Use PTP timestamps for timing
- `--bitrate`: Bitrate for MP3 export in kbps (default: 320)

**Examples:**

```bash
# Export to WAV (default, uncompressed)
dtk media export-audio audio.pcap -o output.wav

# Export to FLAC (lossless compression)
dtk media export-audio audio.pcap -o output.flac --format flac

# Export to MP3 (lossy compression)
dtk media export-audio audio.pcap -o output.mp3 --format mp3 --bitrate 320

# Export specific stream with PTP timing
dtk media export-audio audio.pcap -o output.wav --ssrc 0x12345678 --use-ptp

# Override auto-detection
dtk media export-audio audio.pcap -o output.wav --sample-rate 48000 --bit-depth 24 --channels 2
```

**Supported Audio Formats:**
- **WAV**: Uncompressed PCM audio (16, 24, or 32-bit)
- **FLAC**: Free Lossless Audio Codec (16 or 24-bit)
- **MP3**: MPEG Audio Layer III (lossy, requires FFmpeg)

---

### Export Video (ST 2110-20)

Export video streams from pcap to various video formats:

```bash
dtk media export-video <pcap_file> -o <output_file> [options]
```

**Options:**
- `-o, --output`: Output file path (required)
- `-f, --format`: Output format: `mp4` (default), `mov`, `avi`, or `mkv`
- `-c, --codec`: Video codec: `h264` (default), `h265`, `prores`, or `prores_ks`
- `--ssrc`: Specific SSRC to export (hex)
- `--crf`: Quality for H.264/H.265 (0-51, lower is better, default: 18)
- `--preset`: Encoding speed: `ultrafast`, `fast`, `medium` (default), `slow`, `veryslow`
- `--prores-profile`: ProRes profile: `proxy`, `lt`, `standard` (default), `hq`, `4444`, `4444xq`
- `--use-ptp`: Use PTP timestamps for timing

**Examples:**

```bash
# Export to MP4 with H.264 (most compatible)
dtk media export-video video.pcap -o output.mp4

# Export to MOV with ProRes (for editing)
dtk media export-video video.pcap -o output.mov --codec prores --prores-profile hq

# Export to MP4 with H.265 (better compression)
dtk media export-video video.pcap -o output.mp4 --codec h265 --crf 20 --preset slow

# Export specific stream with PTP timing
dtk media export-video video.pcap -o output.mov --ssrc 0xabcdef --use-ptp
```

**Video Codecs:**

| Codec | Best For | Quality | Speed |
|-------|----------|---------|-------|
| **H.264** | Web playback, compatibility | Good | Fast |
| **H.265** | High quality, smaller files | Better | Slower |
| **ProRes** | Video editing, post-production | Excellent | Medium |
| **ProRes KS** | FFmpeg native ProRes | Excellent | Medium |

**ProRes Profiles:**
- `proxy`: ProRes 422 Proxy (lowest quality, smallest files)
- `lt`: ProRes 422 LT
- `standard`: ProRes 422 (recommended)
- `hq`: ProRes 422 HQ
- `4444`: ProRes 4444 (alpha channel support)
- `4444xq`: ProRes 4444 XQ (highest quality)

---

### Export Ancillary Data (ST 2110-40)

Export ancillary data (captions, timecode, metadata) from pcap:

```bash
dtk media export-anc <pcap_file> -o <output_file> [options]
```

**Options:**
- `-o, --output`: Output file path (required)
- `-f, --format`: Output format: `json` (default), `srt`, `vtt`, `csv`, or `txt`
- `-t, --type`: Data type: `all` (default), `captions`, or `timecode`
- `--ssrc`: Specific SSRC to export (hex)
- `--use-ptp`: Use PTP timestamps for timing

**Examples:**

```bash
# Export all ancillary data to JSON
dtk media export-anc anc.pcap -o output.json

# Export captions to SRT subtitle file
dtk media export-anc anc.pcap -o captions.srt --type captions --format srt

# Export captions to WebVTT
dtk media export-anc anc.pcap -o captions.vtt --type captions --format vtt

# Export timecode to CSV
dtk media export-anc anc.pcap -o timecode.csv --type timecode --format csv

# Export all ANC data as text
dtk media export-anc anc.pcap -o anc_data.txt --format txt --use-ptp
```

**Ancillary Data Types:**

The toolkit automatically detects and decodes:

- **CEA-608/708 Closed Captions** (DID 0x61)
- **SMPTE 12M Timecode** (DID 0x60)
- **AFD/Bar Data** (DID 0x41)
- **SCTE-104 Messages** (DID 0x41)
- **OP-47 Teletext** (DID 0x43)
- **Other SMPTE 291M ANC packets**

**Output Formats:**

| Format | Best For | Type Support |
|--------|----------|--------------|
| **JSON** | All data types, machine-readable | All |
| **SRT** | Captions for video players | Captions only |
| **VTT** | Web captions | Captions only |
| **CSV** | Timecode, spreadsheet analysis | Timecode, All |
| **TXT** | Human-readable dump | All |

---

## Workflow Examples

### Extract Audio from Live Capture

1. Capture audio stream:
```bash
sudo dtk network mcast-join -i eth0 --group 239.0.0.1 --capture 1000 --save audio_capture.pcap
```

2. List streams to verify:
```bash
dtk media list-streams audio_capture.pcap
```

3. Export to WAV:
```bash
dtk media export-audio audio_capture.pcap -o audio.wav
```

### Multi-Stream Export

If a pcap contains multiple streams, export each separately:

```bash
# List streams and note SSRCs
dtk media list-streams multi_stream.pcap

# Export each stream by SSRC
dtk media export-audio multi_stream.pcap -o stream1.wav --ssrc 0x12345678
dtk media export-audio multi_stream.pcap -o stream2.wav --ssrc 0x87654321
```

### Video with Captions

```bash
# Export video
dtk media export-video video.pcap -o video.mp4

# Export captions
dtk media export-anc video.pcap -o captions.srt --type captions --format srt

# Use in video player (VLC, mpv, etc.) - captions will be auto-loaded
```

---

## Technical Details

### Auto-Detection

The toolkit includes intelligent auto-detection for:

- **Sample rates**: 44.1kHz, 48kHz, 88.2kHz, 96kHz
- **Bit depths**: 16-bit, 20-bit, 24-bit
- **Channels**: Mono through 16-channel audio
- **Video resolutions**: 720p, 1080p, 4K UHD, 4K DCI, 8K
- **Frame rates**: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60 fps
- **Pixel formats**: YCbCr 4:2:2, YCbCr 4:4:4, RGB

### PTP Timing

When `--use-ptp` is specified, the toolkit:

1. Extracts PTP timestamps from packets (IEEE 1588)
2. Uses PTP time for precise media synchronization
3. Displays PTP timing information in stream analysis

This is useful when working with PTP-synchronized professional equipment.

### Packet Loss Handling

The RTP extractor automatically:
- Detects and reports missing packets
- Handles out-of-order packets
- Reorders packets by sequence number
- Calculates packet loss percentage

### Performance

Processing times (approximate):
- **Audio export**: ~1-2x realtime
- **Video export**: Depends on codec and resolution
  - H.264 fast preset: ~0.5-1x realtime
  - H.265 slow preset: ~0.1-0.3x realtime
  - ProRes: ~1-2x realtime

---

## Troubleshooting

### "No RTP streams found"

- Verify the pcap contains RTP packets: `dtk network inspect-pcap file.pcap`
- Check that packets have UDP and RTP layers
- Try a different pcap file from the test collection

### "FFmpeg is not installed"

- Install FFmpeg using your package manager (see Prerequisites)
- Verify installation: `ffmpeg -version`

### "FLAC export requires soundfile package"

- Install soundfile: `pip install soundfile`

### Audio/Video Sync Issues

- Use `--use-ptp` for PTP-synchronized equipment
- Verify RTP timestamps are consistent
- Check for packet loss in stream analysis

### Poor Video Quality

- Lower CRF value (e.g., `--crf 12`) for higher quality
- Use slower preset (e.g., `--preset slow`)
- Consider ProRes for lossless/near-lossless quality

---

## API Usage

You can also use the media processing modules in your own Python code:

```python
from dtk.media.rtp_extractor import RTPStreamExtractor
from dtk.media.decoders import ST211030Decoder
from dtk.media.exporters import AudioExporter

# Extract RTP streams
extractor = RTPStreamExtractor(use_ptp=False)
extractor.extract_from_pcap("audio.pcap")

# Get stream info
for ssrc, info in extractor.list_streams():
    print(f"SSRC: {ssrc:#x}, Packets: {info.packet_count}")

# Decode audio
decoder = ST211030Decoder()
packets = extractor.streams[ssrc]
samples = decoder.decode(packets, extractor.stream_info[ssrc])

# Export to file
exporter = AudioExporter()
exporter.export(samples, 48000, "output.wav", format="wav")
```

---

## References

- [SMPTE ST 2110-20: Uncompressed Video](https://www.smpte.org/)
- [SMPTE ST 2110-30: PCM Audio](https://www.smpte.org/)
- [SMPTE ST 2110-40: Ancillary Data](https://www.smpte.org/)
- [SMPTE ST 291: Ancillary Data Packet](https://www.smpte.org/)
- [RTP: RFC 3550](https://tools.ietf.org/html/rfc3550)
- [IEEE 1588: Precision Time Protocol](https://standards.ieee.org/standard/1588-2019.html)
