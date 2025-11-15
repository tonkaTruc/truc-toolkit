"""ST 2110-40 Ancillary Data decoder for metadata, captions, and timecode."""

import struct
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from ..rtp_extractor import RTPPacketInfo, RTPStreamInfo


@dataclass
class ANCPacket:
    """Represents a decoded SMPTE 291M ancillary data packet."""
    did: int  # Data ID
    sdid: int  # Secondary Data ID
    data_count: int  # Data count
    user_data: bytes  # User data words
    checksum: int  # Checksum
    timestamp: float  # RTP timestamp or arrival time
    line_number: Optional[int] = None  # Video line number
    horizontal_offset: Optional[int] = None  # Horizontal offset

    @property
    def did_sdid(self) -> str:
        """Get DID/SDID as hex string."""
        return f"{self.did:02X}/{self.sdid:02X}"

    @property
    def type_name(self) -> str:
        """Get friendly name for this ANC packet type."""
        return ANC_TYPES.get((self.did, self.sdid), "Unknown")


# Common ANC packet types (DID, SDID) -> Name
ANC_TYPES = {
    (0x60, 0x60): "SMPTE 12M Timecode",
    (0x61, 0x01): "CEA-708 Closed Captions",
    (0x61, 0x02): "CEA-608 Closed Captions",
    (0x41, 0x05): "AFD/Bar Data",
    (0x41, 0x07): "SCTE-104 Messages",
    (0x43, 0x02): "OP-47 Teletext (VITC)",
    (0x43, 0x03): "OP-47 Teletext (WSS)",
    (0x51, 0x51): "MPEG Recoding Data",
    (0x64, 0x64): "LTC (Linear Timecode)",
    (0x64, 0x7F): "VITC (Vertical Interval Timecode)",
}


@dataclass
class Timecode:
    """Represents SMPTE 12M timecode."""
    hours: int
    minutes: int
    seconds: int
    frames: int
    drop_frame: bool = False
    timestamp: float = 0.0

    def __str__(self) -> str:
        """Format timecode as HH:MM:SS:FF or HH:MM:SS;FF for drop frame."""
        sep = ';' if self.drop_frame else ':'
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}{sep}{self.frames:02d}"


@dataclass
class Caption:
    """Represents a closed caption."""
    timestamp: float
    text: str
    channel: int = 1  # CC1, CC2, etc.
    type: str = "CEA-608"  # CEA-608 or CEA-708


class ST211040Decoder:
    """Decoder for ST 2110-40 ancillary data streams."""

    def __init__(self):
        """Initialize ancillary data decoder."""
        self.anc_packets: List[ANCPacket] = []
        self.timecodes: List[Timecode] = []
        self.captions: List[Caption] = []

    def decode(self, packets: List[RTPPacketInfo], stream_info: RTPStreamInfo) -> List[ANCPacket]:
        """Decode RTP packets to ancillary data.

        Args:
            packets: List of RTP packets containing ANC data
            stream_info: Information about the RTP stream

        Returns:
            List of decoded ANC packets
        """
        self.anc_packets = []
        self.timecodes = []
        self.captions = []

        for rtp_pkt in packets:
            # Parse ST 2110-40 payload
            anc_pkts = self._parse_st2110_40_payload(rtp_pkt.payload, rtp_pkt.arrival_time)
            self.anc_packets.extend(anc_pkts)

            # Extract specific data types
            for anc in anc_pkts:
                if anc.did == 0x60 and anc.sdid == 0x60:
                    # SMPTE 12M Timecode
                    tc = self._decode_timecode(anc)
                    if tc:
                        self.timecodes.append(tc)

                elif anc.did == 0x61 and anc.sdid in [0x01, 0x02]:
                    # CEA-608/708 Captions
                    captions = self._decode_captions(anc)
                    self.captions.extend(captions)

        return self.anc_packets

    def _parse_st2110_40_payload(self, payload: bytes, timestamp: float) -> List[ANCPacket]:
        """Parse ST 2110-40 RTP payload to extract ANC packets.

        Args:
            payload: RTP payload bytes
            timestamp: Packet timestamp

        Returns:
            List of ANC packets
        """
        anc_packets = []
        offset = 0

        while offset < len(payload):
            # ST 2110-40 uses SMPTE 291M format
            # Each ANC packet starts with: ADF ADF ADF (Ancillary Data Flag)
            # Followed by DID, SDID, DC, UDW[0..DC-1], Checksum

            # Look for ANC packet header (3 bytes: 0x000 0x3FF 0x3FF in 10-bit)
            # In byte stream, this is typically: 0x00 0x00 0x00 or similar pattern
            # For simplicity, we'll look for DID byte pattern

            if offset + 4 > len(payload):
                break

            # Try to parse ANC packet
            try:
                anc = self._parse_anc_packet(payload[offset:], timestamp)
                if anc:
                    anc_packets.append(anc)
                    # Move offset based on packet size
                    offset += 6 + anc.data_count  # Header + data count + checksum
                else:
                    offset += 1  # Move to next byte and try again
            except Exception:
                offset += 1  # Skip bad data

        return anc_packets

    def _parse_anc_packet(self, data: bytes, timestamp: float) -> Optional[ANCPacket]:
        """Parse a single SMPTE 291M ANC packet.

        Args:
            data: Packet data
            timestamp: Timestamp

        Returns:
            ANCPacket or None if parsing fails
        """
        if len(data) < 6:
            return None

        # Parse ANC header
        # Assuming 8-bit packed format for simplicity
        # Real ST 2110-40 uses 10-bit words, but this is a simplified decoder

        did = data[0] & 0xFF
        sdid = data[1] & 0xFF
        data_count = data[2] & 0xFF

        if data_count == 0 or data_count > 255:
            return None

        if len(data) < 4 + data_count:
            return None

        user_data = data[3:3+data_count]
        checksum = data[3+data_count] if len(data) > 3+data_count else 0

        return ANCPacket(
            did=did,
            sdid=sdid,
            data_count=data_count,
            user_data=user_data,
            checksum=checksum,
            timestamp=timestamp
        )

    def _decode_timecode(self, anc: ANCPacket) -> Optional[Timecode]:
        """Decode SMPTE 12M timecode from ANC packet.

        Args:
            anc: ANC packet containing timecode

        Returns:
            Timecode or None
        """
        if len(anc.user_data) < 4:
            return None

        try:
            # SMPTE 12M format (simplified)
            # Byte 0: frames (0-29)
            # Byte 1: seconds (0-59)
            # Byte 2: minutes (0-59)
            # Byte 3: hours (0-23)

            frames = anc.user_data[0] & 0x3F  # Lower 6 bits
            seconds = anc.user_data[1] & 0x7F  # Lower 7 bits
            minutes = anc.user_data[2] & 0x7F  # Lower 7 bits
            hours = anc.user_data[3] & 0x3F  # Lower 6 bits

            # Check for drop frame flag
            drop_frame = bool(anc.user_data[0] & 0x40)

            return Timecode(
                hours=hours,
                minutes=minutes,
                seconds=seconds,
                frames=frames,
                drop_frame=drop_frame,
                timestamp=anc.timestamp
            )
        except Exception:
            return None

    def _decode_captions(self, anc: ANCPacket) -> List[Caption]:
        """Decode CEA-608/708 captions from ANC packet.

        Args:
            anc: ANC packet containing captions

        Returns:
            List of Caption objects
        """
        captions = []

        if anc.sdid == 0x02:  # CEA-608
            captions.extend(self._decode_cea608(anc))
        elif anc.sdid == 0x01:  # CEA-708
            captions.extend(self._decode_cea708(anc))

        return captions

    def _decode_cea608(self, anc: ANCPacket) -> List[Caption]:
        """Decode CEA-608 caption data.

        Args:
            anc: ANC packet

        Returns:
            List of captions
        """
        captions = []

        # CEA-608 uses pairs of bytes
        for i in range(0, len(anc.user_data) - 1, 2):
            byte1 = anc.user_data[i] & 0x7F
            byte2 = anc.user_data[i+1] & 0x7F

            # Skip null pairs
            if byte1 == 0 and byte2 == 0:
                continue

            # Check if it's a control code or character
            if byte1 >= 0x20 and byte2 >= 0x20:
                # Printable characters
                try:
                    text = chr(byte1) + chr(byte2)
                    captions.append(Caption(
                        timestamp=anc.timestamp,
                        text=text,
                        channel=1,
                        type="CEA-608"
                    ))
                except ValueError:
                    pass

        return captions

    def _decode_cea708(self, anc: ANCPacket) -> List[Caption]:
        """Decode CEA-708 caption data.

        Args:
            anc: ANC packet

        Returns:
            List of captions
        """
        # CEA-708 is more complex; simplified implementation
        # Just extract printable ASCII for now
        captions = []

        for byte in anc.user_data:
            if 0x20 <= byte <= 0x7E:
                captions.append(Caption(
                    timestamp=anc.timestamp,
                    text=chr(byte),
                    channel=1,
                    type="CEA-708"
                ))

        return captions

    def get_anc_summary(self) -> Dict[str, int]:
        """Get summary of ANC packet types.

        Returns:
            Dictionary mapping packet type to count
        """
        summary = {}
        for anc in self.anc_packets:
            key = f"{anc.type_name} ({anc.did_sdid})"
            summary[key] = summary.get(key, 0) + 1
        return summary

    def get_timecode_range(self) -> Optional[Tuple[Timecode, Timecode]]:
        """Get first and last timecode.

        Returns:
            Tuple of (first, last) timecode or None
        """
        if not self.timecodes:
            return None
        return (self.timecodes[0], self.timecodes[-1])

    def get_caption_text(self) -> str:
        """Get all caption text concatenated.

        Returns:
            Concatenated caption text
        """
        return ''.join(cap.text for cap in self.captions)
