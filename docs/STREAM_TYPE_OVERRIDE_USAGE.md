# Stream Type Override Usage Guide

## Problem

The RTP stream analyzer auto-detects stream types based on RTP payload type (PT). However, payload types in ST 2110 streams can be ambiguous:

- **PT 98** is commonly used for ST 2110-40 (Ancillary/Meta) but can also be used for audio
- **PT 100** is commonly used for ST 2110-31 (Audio) but could be used for other types
- Dynamic payload types (96-127) can vary by implementation

### Example Issue

```bash
# This ST 2110-31 audio file uses PT 98:
$ dora media list-streams ST2110-31_2ch_PCM_1kHz_20dBFS.pcap

Found 1 RTP stream(s):

SSRC: 0xe003dcb4
  Stream Type: meta        # ❌ WRONG! This is actually audio
  Payload Type: 98 (ST2110-40 Ancillary)
  ...
```

## Solution

Use the `--payload-type` or `--stream-type` options to override the automatic detection.

## Usage

### Override by Payload Type

Override all streams with a specific payload type:

```bash
# Force all PT 98 streams to be detected as audio
$ dora media list-streams ST2110-31_2ch_PCM_1kHz_20dBFS.pcap --payload-type 98=audio

Analyzing pcap file: /path/to/ST2110-31_2ch_PCM_1kHz_20dBFS.pcap
Stream type overrides (by payload type): 1 configured

Found 1 RTP stream(s):

SSRC: 0xe003dcb4
  Stream Type: audio       # ✓ CORRECT! Now detected as audio
  Payload Type: 98 (ST2110-40 Ancillary)
  Packets: 60,766
  Duration: 60.753s
  ...
```

Multiple payload type overrides:

```bash
$ dora media list-streams capture.pcap \
    --payload-type 98=audio \
    --payload-type 100=video
```

### Override by SSRC

Override a specific stream by SSRC (for fine-grained control):

```bash
# Force specific SSRC to be audio (supports hex or decimal)
$ dora media list-streams capture.pcap --stream-type 0xe003dcb4=audio

# Multiple SSRC overrides
$ dora media list-streams capture.pcap \
    --stream-type 0x12345678=audio \
    --stream-type 0xabcdef00=video
```

### Combined Overrides

Combine both methods for maximum flexibility:

```bash
# PT 98 defaults to audio, but SSRC 0xabc is meta
$ dora media list-streams capture.pcap \
    --payload-type 98=audio \
    --stream-type 0xabc=meta
```

## Valid Stream Types

The following stream types are supported:

- `audio` - Audio streams (ST 2110-30, ST 2110-31)
- `video` - Video streams (ST 2110-20)
- `meta` - Metadata/Ancillary streams (ST 2110-40)
- `unknown` - Unrecognized or undefined type

## Override Priority

The detection follows a 3-level priority system:

1. **SSRC override** (highest) - `--stream-type SSRC=type`
2. **Payload type override** (medium) - `--payload-type PT=type`
3. **Auto-detection** (lowest) - Default payload type mapping

This means SSRC overrides always win, even if there's a conflicting payload type override.

### Example Priority

```bash
$ dora media list-streams capture.pcap \
    --payload-type 98=audio \      # PT 98 → audio
    --stream-type 0xabc=video      # SSRC 0xabc → video (overrides PT rule)

# Result:
# - SSRC 0xabc with PT 98 → video (SSRC override wins)
# - Other streams with PT 98 → audio (PT override applies)
# - All other streams → auto-detect
```

## Default Auto-Detection Mappings

Without overrides, the analyzer uses these defaults:

**ST 2110 Media Types:**
- PT 96 → video (ST 2110-20)
- PT 97 → audio (ST 2110-30)
- PT 98 → meta (ST 2110-40)
- PT 100 → audio (ST 2110-31)

**Standard Codecs:**
- PT 0, 3-11, 14 → audio (PCMU, PCMA, G722, L16, etc.)
- PT 26, 31-34 → video (JPEG, H261, H263, MPV, etc.)

## Use Cases

### 1. ST 2110-31 Audio Misdetection

```bash
# ST 2110-31 audio often uses PT 98, which defaults to "meta"
$ dora media list-streams audio.pcap --payload-type 98=audio
```

### 2. Custom Payload Type Mapping

```bash
# Your implementation uses non-standard payload types
$ dora media list-streams capture.pcap \
    --payload-type 102=audio \
    --payload-type 103=video
```

### 3. Mixed Stream Scenarios

```bash
# Most PT 98 is meta, but one specific SSRC is audio
$ dora media list-streams capture.pcap \
    --payload-type 98=meta \
    --stream-type 0x12345678=audio
```

### 4. Export Commands

The override options also work with export commands:

```bash
# Export audio even though PT 98 defaults to meta
$ dora media export-audio audio.pcap -o output.wav --payload-type 98=audio
```

## Programmatic Usage

You can also use overrides in Python code:

```python
from dtk.media.rtp_extractor import RTPStreamExtractor

# Payload type override
extractor = RTPStreamExtractor(payload_type_override={98: "audio"})
extractor.extract_from_pcap("capture.pcap")

# SSRC override
extractor = RTPStreamExtractor(stream_type_override={0x12345678: "audio"})
extractor.extract_from_pcap("capture.pcap")

# Both
extractor = RTPStreamExtractor(
    payload_type_override={98: "audio"},
    stream_type_override={0xabcdef00: "video"}
)
extractor.extract_from_pcap("capture.pcap")
```

## Validation

The CLI validates your override values:

```bash
# Invalid stream type
$ dora media list-streams capture.pcap --payload-type 98=foo
Error: Invalid stream type 'foo'. Must be: audio, video, meta, or unknown

# Invalid format
$ dora media list-streams capture.pcap --payload-type 98:audio
Error: Invalid payload-type format '98:audio'. Use PT=type (e.g., 98=audio)
```

## Testing

Run the test suite to verify override functionality:

```bash
$ python tests/media/test_stream_type_detection.py

Test 1: Auto-Detection of Stream Types
  ✓ All tests passed

Test 2: Manual Stream Type Override (by SSRC)
  ✓ All tests passed

Test 3: Manual Stream Type Override (by Payload Type)
  ✓ All tests passed

Test 4: Override Priority (SSRC > Payload Type > Auto-detect)
  ✓ All tests passed

Test 5: PCAP Integration
  ✓ Tests passed

Result: 5/5 test suites passed
```

## Summary

- Use `--payload-type PT=type` to override detection for all streams with a specific payload type
- Use `--stream-type SSRC=type` to override detection for a specific stream
- SSRC overrides take priority over payload type overrides
- Valid types: `audio`, `video`, `meta`, `unknown`
- Works with all media commands: `list-streams`, `export-audio`, `export-video`, `export-anc`
