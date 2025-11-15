#!/usr/bin/env python3
"""Manual test of RTP parsing from UDP packets."""

import struct
from pathlib import Path

def parse_rtp_from_udp(udp_payload: bytes):
    """Parse RTP header from UDP payload - manual implementation for testing."""
    if len(udp_payload) < 12:
        return None

    # Parse first byte: V(2), P(1), X(1), CC(4)
    first_byte = udp_payload[0]
    version = (first_byte >> 6) & 0x03
    padding = (first_byte >> 5) & 0x01
    extension = (first_byte >> 4) & 0x01
    csrc_count = first_byte & 0x0F

    # Validate RTP version 2
    if version != 2:
        return None

    # Parse second byte: M(1), PT(7)
    second_byte = udp_payload[1]
    marker = (second_byte >> 7) & 0x01
    payload_type = second_byte & 0x7F

    # Parse rest of fixed header
    sequence = struct.unpack('!H', udp_payload[2:4])[0]
    timestamp = struct.unpack('!I', udp_payload[4:8])[0]
    ssrc = struct.unpack('!I', udp_payload[8:12])[0]

    # Calculate header size
    header_size = 12  # Base header
    header_size += csrc_count * 4

    if len(udp_payload) < header_size:
        return None

    # Handle extension header if present
    if extension:
        if len(udp_payload) < header_size + 4:
            return None
        ext_length = struct.unpack('!H', udp_payload[header_size + 2:header_size + 4])[0]
        header_size += 4 + (ext_length * 4)
        if len(udp_payload) < header_size:
            return None

    # Handle padding
    payload_start = header_size
    payload_end = len(udp_payload)

    if padding and len(udp_payload) > header_size:
        padding_length = udp_payload[-1]
        if padding_length > 0 and padding_length <= (len(udp_payload) - header_size):
            payload_end -= padding_length

    payload = udp_payload[payload_start:payload_end]

    return {
        'version': version,
        'padding': bool(padding),
        'extension': bool(extension),
        'csrc_count': csrc_count,
        'marker': bool(marker),
        'payload_type': payload_type,
        'sequence': sequence,
        'timestamp': timestamp,
        'ssrc': ssrc,
        'payload_size': len(payload),
        'header_size': header_size
    }


def test_rtp_parsing():
    """Test RTP parsing with sample data."""
    print("="*80)
    print("RTP Parser Manual Validation Test")
    print("="*80)

    # Test case 1: Minimal RTP packet (version 2, no padding, no extension, no CSRC)
    # V=2, P=0, X=0, CC=0, M=0, PT=96 (ST2110-20)
    # Sequence=1000, Timestamp=90000, SSRC=0x12345678
    test_packet_1 = bytes([
        0x80,  # V=2, P=0, X=0, CC=0
        0x60,  # M=0, PT=96
        0x03, 0xE8,  # Sequence=1000
        0x00, 0x01, 0x5F, 0x90,  # Timestamp=90000
        0x12, 0x34, 0x56, 0x78,  # SSRC
        # Payload follows...
        0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE
    ])

    print("\nTest 1: Basic RTP packet (no CSRC, no extension, no padding)")
    result = parse_rtp_from_udp(test_packet_1)
    if result:
        print(f"  ✓ Parsed successfully")
        print(f"    Version: {result['version']}")
        print(f"    Payload Type: {result['payload_type']}")
        print(f"    Sequence: {result['sequence']}")
        print(f"    Timestamp: {result['timestamp']}")
        print(f"    SSRC: {result['ssrc']:#010x}")
        print(f"    Header Size: {result['header_size']} bytes")
        print(f"    Payload Size: {result['payload_size']} bytes")
    else:
        print("  ✗ Failed to parse")
        return False

    # Test case 2: RTP packet with 2 CSRC identifiers
    test_packet_2 = bytes([
        0x82,  # V=2, P=0, X=0, CC=2
        0xE1,  # M=1, PT=97 (ST2110-30)
        0x00, 0x10,  # Sequence=16
        0x00, 0x00, 0x10, 0x00,  # Timestamp=4096
        0xAA, 0xBB, 0xCC, 0xDD,  # SSRC
        0x11, 0x11, 0x11, 0x11,  # CSRC[0]
        0x22, 0x22, 0x22, 0x22,  # CSRC[1]
        # Payload
        0x00, 0x11, 0x22, 0x33
    ])

    print("\nTest 2: RTP packet with CSRC identifiers")
    result = parse_rtp_from_udp(test_packet_2)
    if result:
        print(f"  ✓ Parsed successfully")
        print(f"    CSRC Count: {result['csrc_count']}")
        print(f"    Marker: {result['marker']}")
        print(f"    Payload Type: {result['payload_type']}")
        print(f"    Header Size: {result['header_size']} bytes (12 + {result['csrc_count']*4})")
        print(f"    Payload Size: {result['payload_size']} bytes")
    else:
        print("  ✗ Failed to parse")
        return False

    # Test case 3: Invalid version (should fail)
    test_packet_3 = bytes([
        0x40,  # V=1, P=0, X=0, CC=0 (wrong version!)
        0x60, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x12, 0x34, 0x56, 0x78
    ])

    print("\nTest 3: Invalid RTP version (should reject)")
    result = parse_rtp_from_udp(test_packet_3)
    if result is None:
        print("  ✓ Correctly rejected non-v2 packet")
    else:
        print("  ✗ Should have rejected this packet")
        return False

    # Test case 4: Too short (should fail)
    test_packet_4 = bytes([0x80, 0x60, 0x00, 0x01])  # Only 4 bytes

    print("\nTest 4: Truncated packet (should reject)")
    result = parse_rtp_from_udp(test_packet_4)
    if result is None:
        print("  ✓ Correctly rejected truncated packet")
    else:
        print("  ✗ Should have rejected this packet")
        return False

    print("\n" + "="*80)
    print("✓ All manual tests PASSED")
    print("="*80)
    return True


if __name__ == "__main__":
    import sys
    success = test_rtp_parsing()
    sys.exit(0 if success else 1)
