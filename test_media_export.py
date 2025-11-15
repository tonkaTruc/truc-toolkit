#!/usr/bin/env python3
"""Test script for media export functionality."""

import sys
import os
from pathlib import Path

# Suppress all warnings and stderr temporarily for Scapy import
import warnings
warnings.filterwarnings('ignore')
os.environ['SCAPY_NO_WARNINGS'] = '1'

# Add toolkit to path
sys.path.insert(0, str(Path(__file__).parent))

# Import but catch any errors
try:
    from dtk.media.rtp_extractor import RTPStreamExtractor
    print("✓ Successfully imported RTP extractor")
except Exception as e:
    print(f"✗ Failed to import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def test_list_streams():
    """Test listing RTP streams from a pcap file."""
    pcap_path = "/home/user/toolkit/Resources/cap_store/ST2110-30_SxTAG_1.pcapng"

    print(f"\nTesting RTP stream extraction from: {pcap_path}")
    print("=" * 70)

    try:
        # Extract streams
        extractor = RTPStreamExtractor(use_ptp=False)
        print("✓ Created RTPStreamExtractor")

        extractor.extract_from_pcap(pcap_path)
        print("✓ Extracted streams from pcap")

        streams = extractor.list_streams()

        if not streams:
            print("✗ No RTP streams found!")
            # Debug: check if any packets were read
            print(f"Debug: Number of SSRCs in streams dict: {len(extractor.streams)}")
            return False

        print(f"\n✓ Found {len(streams)} RTP stream(s):\n")

        for ssrc, info in streams:
            print(f"SSRC: {ssrc:#010x}")
            print(f"  Payload Type: {info.payload_type} ({extractor.get_payload_type_name(info.payload_type)})")
            print(f"  Packets: {info.packet_count}")
            print(f"  Sequence: {info.first_seq} -> {info.last_seq}")
            print(f"  Timestamp Range: {info.first_timestamp} -> {info.last_timestamp}")
            print(f"  Duration: {info.duration:.3f}s")
            print(f"  Packets Lost: {info.packets_lost} ({info.packet_loss_rate:.2f}%)")
            print(f"  Out of Order: {info.packets_out_of_order}")
            print()

        return True

    except Exception as e:
        print(f"✗ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_list_streams()
    print("\n" + "=" * 70)
    if success:
        print("✓ Test PASSED")
    else:
        print("✗ Test FAILED")
    sys.exit(0 if success else 1)
