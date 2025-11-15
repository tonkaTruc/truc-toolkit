"""Ancillary data exporter for captions, timecode, and metadata."""

import json
from pathlib import Path
from typing import List, Optional
from datetime import timedelta


class AncillaryExporter:
    """Export ancillary data to various formats."""

    SUPPORTED_FORMATS = ['srt', 'vtt', 'csv', 'json', 'txt']

    def __init__(self):
        """Initialize ancillary data exporter."""
        self.last_export_path: Optional[str] = None

    def export_captions(self, captions: List, output_path: str,
                       format: str = 'srt', **kwargs) -> str:
        """Export captions to subtitle file.

        Args:
            captions: List of Caption objects
            output_path: Output file path
            format: Output format ('srt', 'vtt')
            **kwargs: Additional options

        Returns:
            Path to exported file

        Raises:
            ValueError: If format is not supported
        """
        format = format.lower()

        if format not in ['srt', 'vtt']:
            raise ValueError(f"Unsupported caption format: {format}")

        output_path = self._ensure_extension(output_path, format)

        if format == 'srt':
            self._export_srt(captions, output_path)
        elif format == 'vtt':
            self._export_vtt(captions, output_path)

        self.last_export_path = output_path
        return output_path

    def export_timecode(self, timecodes: List, output_path: str,
                       format: str = 'csv', **kwargs) -> str:
        """Export timecode data.

        Args:
            timecodes: List of Timecode objects
            output_path: Output file path
            format: Output format ('csv', 'txt', 'json')
            **kwargs: Additional options

        Returns:
            Path to exported file
        """
        format = format.lower()

        if format not in ['csv', 'txt', 'json']:
            raise ValueError(f"Unsupported timecode format: {format}")

        output_path = self._ensure_extension(output_path, format)

        if format == 'csv':
            self._export_timecode_csv(timecodes, output_path)
        elif format == 'txt':
            self._export_timecode_txt(timecodes, output_path)
        elif format == 'json':
            self._export_timecode_json(timecodes, output_path)

        self.last_export_path = output_path
        return output_path

    def export_anc_packets(self, anc_packets: List, output_path: str,
                          format: str = 'json', **kwargs) -> str:
        """Export all ANC packets.

        Args:
            anc_packets: List of ANCPacket objects
            output_path: Output file path
            format: Output format ('json', 'txt', 'csv')
            **kwargs: Additional options

        Returns:
            Path to exported file
        """
        format = format.lower()

        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}")

        output_path = self._ensure_extension(output_path, format)

        if format == 'json':
            self._export_anc_json(anc_packets, output_path)
        elif format == 'txt':
            self._export_anc_txt(anc_packets, output_path)
        elif format == 'csv':
            self._export_anc_csv(anc_packets, output_path)

        self.last_export_path = output_path
        return output_path

    def _ensure_extension(self, path: str, format: str) -> str:
        """Ensure file path has correct extension.

        Args:
            path: File path
            format: Desired format

        Returns:
            Path with correct extension
        """
        p = Path(path)
        if p.suffix.lower() != f'.{format}':
            return str(p.with_suffix(f'.{format}'))
        return path

    def _export_srt(self, captions: List, output_path: str):
        """Export captions to SRT format.

        Args:
            captions: List of Caption objects
            output_path: Output file path
        """
        # Group captions into subtitle entries
        # Each caption is typically very short, so we'll group by timing
        entries = self._group_captions_for_subtitles(captions)

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, (start, end, text) in enumerate(entries, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_srt_time(start)} --> {self._format_srt_time(end)}\n")
                f.write(f"{text}\n\n")

    def _export_vtt(self, captions: List, output_path: str):
        """Export captions to WebVTT format.

        Args:
            captions: List of Caption objects
            output_path: Output file path
        """
        entries = self._group_captions_for_subtitles(captions)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")

            for i, (start, end, text) in enumerate(entries, 1):
                f.write(f"{i}\n")
                f.write(f"{self._format_vtt_time(start)} --> {self._format_vtt_time(end)}\n")
                f.write(f"{text}\n\n")

    def _group_captions_for_subtitles(self, captions: List,
                                     duration: float = 2.0) -> List[tuple]:
        """Group captions into subtitle entries with timing.

        Args:
            captions: List of Caption objects
            duration: Duration for each subtitle in seconds

        Returns:
            List of (start_time, end_time, text) tuples
        """
        if not captions:
            return []

        entries = []
        current_text = ""
        start_time = captions[0].timestamp
        last_time = start_time

        for cap in captions:
            # If time gap is too large, create new entry
            if cap.timestamp - last_time > duration:
                if current_text:
                    entries.append((start_time, last_time + duration, current_text.strip()))
                current_text = cap.text
                start_time = cap.timestamp
            else:
                current_text += cap.text

            last_time = cap.timestamp

        # Add final entry
        if current_text:
            entries.append((start_time, last_time + duration, current_text.strip()))

        return entries

    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format (HH:MM:SS,mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((td.total_seconds() % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for WebVTT format (HH:MM:SS.mmm).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        millis = int((td.total_seconds() % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _export_timecode_csv(self, timecodes: List, output_path: str):
        """Export timecode to CSV format.

        Args:
            timecodes: List of Timecode objects
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Frame,Timecode,Hours,Minutes,Seconds,Frames,Drop_Frame,Timestamp\n")

            for i, tc in enumerate(timecodes):
                f.write(f"{i},{tc},{tc.hours},{tc.minutes},{tc.seconds},"
                       f"{tc.frames},{tc.drop_frame},{tc.timestamp}\n")

    def _export_timecode_txt(self, timecodes: List, output_path: str):
        """Export timecode to text format.

        Args:
            timecodes: List of Timecode objects
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Timecode Log\n")
            f.write("=" * 50 + "\n\n")

            for i, tc in enumerate(timecodes):
                f.write(f"Frame {i:6d}: {tc}  (timestamp: {tc.timestamp:.3f}s)\n")

    def _export_timecode_json(self, timecodes: List, output_path: str):
        """Export timecode to JSON format.

        Args:
            timecodes: List of Timecode objects
            output_path: Output file path
        """
        data = []
        for i, tc in enumerate(timecodes):
            data.append({
                'frame': i,
                'timecode': str(tc),
                'hours': tc.hours,
                'minutes': tc.minutes,
                'seconds': tc.seconds,
                'frames': tc.frames,
                'drop_frame': tc.drop_frame,
                'timestamp': tc.timestamp
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _export_anc_json(self, anc_packets: List, output_path: str):
        """Export ANC packets to JSON format.

        Args:
            anc_packets: List of ANCPacket objects
            output_path: Output file path
        """
        data = []
        for anc in anc_packets:
            data.append({
                'did': f"0x{anc.did:02X}",
                'sdid': f"0x{anc.sdid:02X}",
                'type': anc.type_name,
                'data_count': anc.data_count,
                'user_data': anc.user_data.hex(),
                'checksum': f"0x{anc.checksum:02X}",
                'timestamp': anc.timestamp
            })

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _export_anc_txt(self, anc_packets: List, output_path: str):
        """Export ANC packets to text format.

        Args:
            anc_packets: List of ANCPacket objects
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Ancillary Data Packets\n")
            f.write("=" * 70 + "\n\n")

            for i, anc in enumerate(anc_packets):
                f.write(f"Packet {i}:\n")
                f.write(f"  Type: {anc.type_name}\n")
                f.write(f"  DID/SDID: {anc.did_sdid}\n")
                f.write(f"  Data Count: {anc.data_count}\n")
                f.write(f"  User Data: {anc.user_data.hex()}\n")
                f.write(f"  Timestamp: {anc.timestamp:.3f}s\n")
                f.write("\n")

    def _export_anc_csv(self, anc_packets: List, output_path: str):
        """Export ANC packets to CSV format.

        Args:
            anc_packets: List of ANCPacket objects
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Packet,Type,DID,SDID,Data_Count,User_Data,Timestamp\n")

            for i, anc in enumerate(anc_packets):
                f.write(f"{i},{anc.type_name},0x{anc.did:02X},0x{anc.sdid:02X},"
                       f"{anc.data_count},{anc.user_data.hex()},{anc.timestamp}\n")
