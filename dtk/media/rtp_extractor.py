"""RTP stream extraction and reassembly from pcap files."""

import struct
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class RTPPacketInfo:
    """Information about an RTP packet."""
    sequence: int
    timestamp: int
    ssrc: int
    payload_type: int
    marker: bool
    payload: bytes
    arrival_time: float  # Packet arrival time in seconds
    ptp_timestamp: Optional[int] = None  # PTP timestamp if available


@dataclass
class RTPStreamInfo:
    """Information about an RTP stream."""
    ssrc: int
    payload_type: int
    packet_count: int
    first_seq: int
    last_seq: int
    first_timestamp: int
    last_timestamp: int
    packets_lost: int
    packets_out_of_order: int
    start_time: float
    end_time: float
    has_ptp: bool = False

    @property
    def duration(self) -> float:
        """Get stream duration in seconds."""
        return self.end_time - self.start_time

    @property
    def packet_loss_rate(self) -> float:
        """Calculate packet loss rate as percentage."""
        total_expected = (self.last_seq - self.first_seq + 1) & 0xFFFF
        if total_expected == 0:
            return 0.0
        return (self.packets_lost / total_expected) * 100.0


class RTPStreamExtractor:
    """Extract and reassemble RTP streams from pcap files."""

    # Common RTP payload types for ST 2110
    PAYLOAD_TYPES = {
        96: "ST2110-20 Video",
        97: "ST2110-30 Audio",
        98: "ST2110-40 Ancillary",
        # Dynamic payload types can vary
    }

    def __init__(self, use_ptp: bool = False):
        """Initialize RTP stream extractor.

        Args:
            use_ptp: Whether to extract and use PTP timestamps
        """
        self.use_ptp = use_ptp
        self.streams: Dict[int, List[RTPPacketInfo]] = defaultdict(list)
        self.stream_info: Dict[int, RTPStreamInfo] = {}

    def _parse_rtp_from_udp(self, udp_payload: bytes) -> Optional[Tuple[dict, bytes]]:
        """Parse RTP header from UDP payload.

        Args:
            udp_payload: Raw UDP payload bytes

        Returns:
            Tuple of (RTP header dict, payload bytes) or None if not valid RTP
        """
        # Need at least 12 bytes for minimum RTP header
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

        # Add CSRC identifiers (4 bytes each)
        header_size += csrc_count * 4

        # Check if we have enough data for CSRC list
        if len(udp_payload) < header_size:
            return None

        # Handle extension header if present
        if extension:
            # Extension header is at least 4 bytes (16-bit profile + 16-bit length)
            if len(udp_payload) < header_size + 4:
                return None

            # Get extension length (in 32-bit words, excluding the 4-byte extension header itself)
            ext_length = struct.unpack('!H', udp_payload[header_size + 2:header_size + 4])[0]
            header_size += 4 + (ext_length * 4)

            # Verify we have enough data
            if len(udp_payload) < header_size:
                return None

        # Handle padding if present
        payload_start = header_size
        payload_end = len(udp_payload)

        if padding and len(udp_payload) > header_size:
            # Last byte indicates padding length
            padding_length = udp_payload[-1]
            if padding_length > 0 and padding_length <= (len(udp_payload) - header_size):
                payload_end -= padding_length

        # Extract payload
        payload = udp_payload[payload_start:payload_end]

        # Build RTP header info dict
        rtp_header = {
            'version': version,
            'padding': bool(padding),
            'extension': bool(extension),
            'csrc_count': csrc_count,
            'marker': bool(marker),
            'payload_type': payload_type,
            'sequence': sequence,
            'timestamp': timestamp,
            'ssrc': ssrc
        }

        return rtp_header, payload

    def extract_from_pcap(self, pcap_path: str) -> Dict[int, List[RTPPacketInfo]]:
        """Extract all RTP streams from a pcap file.

        Args:
            pcap_path: Path to the pcap file

        Returns:
            Dictionary mapping SSRC to list of RTP packets
        """
        from scapy.all import rdpcap, UDP, IP
        from scapy.layers.rtp import RTP

        self.streams.clear()
        self.stream_info.clear()

        packets = rdpcap(pcap_path)

        for pkt in packets:
            # First, try to check if Scapy already parsed RTP
            if pkt.haslayer(RTP):
                rtp = pkt[RTP]
                arrival_time = float(pkt.time)

                # Extract PTP timestamp if requested
                ptp_timestamp = None
                if self.use_ptp:
                    ptp_timestamp = self._extract_ptp_timestamp(pkt)

                # Create RTP packet info
                rtp_info = RTPPacketInfo(
                    sequence=rtp.sequence,
                    timestamp=rtp.timestamp,
                    ssrc=rtp.sourcesync,
                    payload_type=rtp.payload_type,
                    marker=bool(rtp.marker),
                    payload=bytes(rtp.payload),
                    arrival_time=arrival_time,
                    ptp_timestamp=ptp_timestamp
                )

                self.streams[rtp.sourcesync].append(rtp_info)

            # If not, try to manually parse RTP from UDP payload (for ST 2110)
            elif pkt.haslayer(UDP):
                udp = pkt[UDP]
                udp_payload = bytes(udp.payload)

                # Try to parse RTP from UDP payload
                rtp_data = self._parse_rtp_from_udp(udp_payload)
                if rtp_data is None:
                    continue

                rtp_header, payload = rtp_data
                arrival_time = float(pkt.time)

                # Extract PTP timestamp if requested
                ptp_timestamp = None
                if self.use_ptp:
                    ptp_timestamp = self._extract_ptp_timestamp(pkt)

                # Create RTP packet info
                rtp_info = RTPPacketInfo(
                    sequence=rtp_header['sequence'],
                    timestamp=rtp_header['timestamp'],
                    ssrc=rtp_header['ssrc'],
                    payload_type=rtp_header['payload_type'],
                    marker=rtp_header['marker'],
                    payload=payload,
                    arrival_time=arrival_time,
                    ptp_timestamp=ptp_timestamp
                )

                self.streams[rtp_header['ssrc']].append(rtp_info)

        # Sort packets by sequence number and analyze streams
        for ssrc in self.streams:
            self.streams[ssrc].sort(key=lambda p: p.sequence)
            self.stream_info[ssrc] = self._analyze_stream(self.streams[ssrc])

        return self.streams

    def _extract_ptp_timestamp(self, packet) -> Optional[int]:
        """Extract PTP timestamp from packet if available.

        Args:
            packet: Scapy packet

        Returns:
            PTP timestamp in nanoseconds or None
        """
        # Check if packet has PTP layer
        try:
            from dtk.custom_headers.PTP import PTPv2
            if packet.haslayer(PTPv2):
                ptp = packet[PTPv2]
                # PTP timestamp is in seconds and nanoseconds
                # Combine into total nanoseconds
                if hasattr(ptp, 'seconds') and hasattr(ptp, 'nanoseconds'):
                    return int(ptp.seconds) * 1_000_000_000 + int(ptp.nanoseconds)
        except (ImportError, AttributeError):
            pass

        return None

    def _analyze_stream(self, packets: List[RTPPacketInfo]) -> RTPStreamInfo:
        """Analyze an RTP stream and gather statistics.

        Args:
            packets: List of RTP packets in sequence order

        Returns:
            Stream information and statistics
        """
        if not packets:
            raise ValueError("Cannot analyze empty stream")

        first_pkt = packets[0]
        last_pkt = packets[-1]

        # Count packet loss and out-of-order packets
        packets_lost = 0
        packets_out_of_order = 0
        expected_seq = first_pkt.sequence

        for pkt in packets:
            seq_diff = (pkt.sequence - expected_seq) & 0xFFFF
            if seq_diff > 0:
                packets_lost += seq_diff
            elif seq_diff < 0:
                packets_out_of_order += 1
            expected_seq = (pkt.sequence + 1) & 0xFFFF

        # Check if stream has PTP timestamps
        has_ptp = any(p.ptp_timestamp is not None for p in packets)

        return RTPStreamInfo(
            ssrc=first_pkt.ssrc,
            payload_type=first_pkt.payload_type,
            packet_count=len(packets),
            first_seq=first_pkt.sequence,
            last_seq=last_pkt.sequence,
            first_timestamp=first_pkt.timestamp,
            last_timestamp=last_pkt.timestamp,
            packets_lost=packets_lost,
            packets_out_of_order=packets_out_of_order,
            start_time=first_pkt.arrival_time,
            end_time=last_pkt.arrival_time,
            has_ptp=has_ptp
        )

    def get_stream_info(self, ssrc: Optional[int] = None) -> Dict[int, RTPStreamInfo]:
        """Get information about RTP streams.

        Args:
            ssrc: Specific SSRC to get info for, or None for all streams

        Returns:
            Dictionary mapping SSRC to stream info
        """
        if ssrc is not None:
            return {ssrc: self.stream_info[ssrc]} if ssrc in self.stream_info else {}
        return self.stream_info.copy()

    def get_payload_data(self, ssrc: int) -> bytes:
        """Get reassembled payload data for a stream.

        Args:
            ssrc: SSRC of the stream

        Returns:
            Concatenated payload bytes
        """
        if ssrc not in self.streams:
            raise ValueError(f"No stream found with SSRC {ssrc:#x}")

        return b''.join(pkt.payload for pkt in self.streams[ssrc])

    def get_payload_type_name(self, payload_type: int) -> str:
        """Get friendly name for payload type.

        Args:
            payload_type: RTP payload type number

        Returns:
            Friendly name or "Unknown"
        """
        return self.PAYLOAD_TYPES.get(payload_type, f"Unknown (PT {payload_type})")

    def list_streams(self) -> List[Tuple[int, RTPStreamInfo]]:
        """Get list of all streams sorted by SSRC.

        Returns:
            List of (SSRC, StreamInfo) tuples
        """
        return sorted(self.stream_info.items())
