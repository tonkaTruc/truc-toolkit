#!/usr/bin/env python3
"""Test RTP extraction from ST 2110 pcap files using dpkt."""

import sys
import struct
from pathlib import Path
import dpkt


def parse_rtp_from_udp(udp_payload: bytes):
    """Parse RTP header from UDP payload."""
    if len(udp_payload) < 12:
        return None

    first_byte = udp_payload[0]
    version = (first_byte >> 6) & 0x03

    if version != 2:
        return None

    padding = (first_byte >> 5) & 0x01
    extension = (first_byte >> 4) & 0x01
    csrc_count = first_byte & 0x0F

    second_byte = udp_payload[1]
    marker = (second_byte >> 7) & 0x01
    payload_type = second_byte & 0x7F

    sequence = struct.unpack('!H', udp_payload[2:4])[0]
    timestamp = struct.unpack('!I', udp_payload[4:8])[0]
    ssrc = struct.unpack('!I', udp_payload[8:12])[0]

    header_size = 12 + csrc_count * 4

    if len(udp_payload) < header_size:
        return None

    if extension:
        if len(udp_payload) < header_size + 4:
            return None
        ext_length = struct.unpack('!H', udp_payload[header_size + 2:header_size + 4])[0]
        header_size += 4 + (ext_length * 4)
        if len(udp_payload) < header_size:
            return None

    payload_start = header_size
    payload_end = len(udp_payload)

    if padding and len(udp_payload) > header_size:
        padding_length = udp_payload[-1]
        if padding_length > 0 and padding_length <= (len(udp_payload) - header_size):
            payload_end -= padding_length

    return {
        'payload_type': payload_type,
        'sequence': sequence,
        'timestamp': timestamp,
        'ssrc': ssrc,
        'marker': bool(marker),
        'payload_size': payload_end - payload_start,
        'header_size': header_size
    }


def test_pcap_file(pcap_path: str):
    """Test RTP detection in a pcap file."""
    print(f"\n{'='*80}")
    print(f"Testing: {Path(pcap_path).name}")
    print('='*80)

    if not Path(pcap_path).exists():
        print(f"✗ File not found")
        return False

    try:
        with open(pcap_path, 'rb') as f:
            # Try pcapng first, then pcap
            try:
                pcap = dpkt.pcapng.Reader(f)
            except:
                f.seek(0)
                pcap = dpkt.pcap.Reader(f)

            rtp_streams = {}
            total_packets = 0
            udp_count = 0
            rtp_count = 0

            for timestamp, buf in pcap:
                total_packets += 1

                # Parse Ethernet
                try:
                    eth = dpkt.ethernet.Ethernet(buf)
                except:
                    continue

                # Check for IP
                if not isinstance(eth.data, (dpkt.ip.IP, dpkt.ip6.IP6)):
                    continue

                ip = eth.data

                # Check for UDP
                if not isinstance(ip.data, dpkt.udp.UDP):
                    continue

                udp = ip.data
                udp_count += 1

                # Try to parse as RTP
                rtp_info = parse_rtp_from_udp(udp.data)
                if rtp_info:
                    rtp_count += 1
                    ssrc = rtp_info['ssrc']

                    if ssrc not in rtp_streams:
                        rtp_streams[ssrc] = {
                            'packets': [],
                            'payload_type': rtp_info['payload_type'],
                            'total_payload': 0,
                            'first_ts': timestamp,
                            'last_ts': timestamp
                        }

                    rtp_streams[ssrc]['packets'].append(rtp_info)
                    rtp_streams[ssrc]['total_payload'] += rtp_info['payload_size']
                    rtp_streams[ssrc]['last_ts'] = timestamp

        print(f"Total packets: {total_packets:,}")
        print(f"UDP packets: {udp_count:,}")
        print(f"RTP packets detected: {rtp_count:,}")
        print(f"RTP streams found: {len(rtp_streams)}")

        if len(rtp_streams) == 0:
            print("✗ No RTP streams detected")
            return False

        print(f"\n{'Stream Details:':-^80}")

        for ssrc, stream_data in sorted(rtp_streams.items()):
            packets_list = stream_data['packets']
            pt = stream_data['payload_type']

            pt_name = {
                96: "ST2110-20 Video",
                97: "ST2110-30 Audio",
                98: "ST2110-40 Anc"
            }.get(pt, f"PT {pt}")

            first_seq = packets_list[0]['sequence']
            last_seq = packets_list[-1]['sequence']
            first_rtp_ts = packets_list[0]['timestamp']
            last_rtp_ts = packets_list[-1]['timestamp']

            duration = stream_data['last_ts'] - stream_data['first_ts']

            # Calculate packet loss
            expected_packets = ((last_seq - first_seq + 1) & 0xFFFF)
            packets_lost = expected_packets - len(packets_list)
            loss_rate = (packets_lost / expected_packets * 100) if expected_packets > 0 else 0

            print(f"\nSSRC: {ssrc:#010x}")
            print(f"  Type: {pt_name}")
            print(f"  Packets: {len(packets_list):,}")
            print(f"  Sequence Range: {first_seq} → {last_seq}")
            print(f"  RTP Timestamp: {first_rtp_ts:#010x} → {last_rtp_ts:#010x}")
            print(f"  Duration: {duration:.3f}s")
            print(f"  Total Payload: {stream_data['total_payload']:,} bytes")
            print(f"  Avg Payload/Pkt: {stream_data['total_payload']/len(packets_list):.1f} bytes")
            print(f"  Packet Loss: {packets_lost} ({loss_rate:.2f}%)")

        print(f"\n{'='*80}")
        print(f"✓ Successfully detected {len(rtp_streams)} RTP stream(s)")
        print(f"{'='*80}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests on ST 2110 pcap files."""
    # Get project root (tests/media -> tests -> toolkit)
    project_root = Path(__file__).parent.parent.parent

    test_files = [
        project_root / "Resources/cap_store/ST2110-30_SxTAG_1.pcapng",
        project_root / "Resources/cap_store/ST2110-30_SxTAG_2.pcapng",
        project_root / "Resources/cap_store/ST2110-31_2ch_PCM_1kHz_20dBFS.pcap",
        project_root / "Resources/cap_store/ST2110-31_DolbyD_20_192kbps_1kHz.pcap",
    ]

    print("="*80)
    print("ST 2110 RTP Stream Detection Validation Test")
    print("="*80)
    print("\nThis test validates that the RTP parser correctly identifies and")
    print("parses RTP streams in ST 2110 UDP packets from pcap files.")

    results = {}
    for pcap_file in test_files:
        if pcap_file.exists():
            results[pcap_file.name] = test_pcap_file(str(pcap_file))
        else:
            print(f"\n✗ File not found: {pcap_file}")

    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print("="*80)

    for filename, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} {filename}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print("="*80)
    if total > 0:
        print(f"Result: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    else:
        print("Result: No tests found")
    print("="*80)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
