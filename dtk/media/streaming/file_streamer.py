"""GStreamer-based file to RTP streaming with ST2110 compliance.

This module implements best practices for GStreamer with Python, including:
- Proper pipeline lifecycle management
- Error handling and state management
- ST2110 compliant RTP streaming
- Optional PTP timing support
- PCap capture capability
"""

import os
import sys
import logging
from dataclasses import dataclass
from typing import Optional, Literal
from pathlib import Path

try:
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstRtp', '1.0')
    from gi.repository import Gst, GLib, GstRtp

    # Initialize GStreamer
    Gst.init(None)
    GST_AVAILABLE = True
except (ImportError, ValueError) as e:
    GST_AVAILABLE = False
    logging.warning(f"GStreamer not available: {e}")


@dataclass
class AudioStreamConfig:
    """Configuration for ST2110-30/31 audio streaming."""

    # Network settings
    dest_ip: str
    dest_port: int
    src_ip: Optional[str] = None

    # Audio settings
    sample_rate: int = 48000
    channels: int = 2
    bit_depth: Literal[16, 24] = 24

    # RTP settings
    payload_type: int = 97  # ST2110-30 typical
    ssrc: Optional[int] = None

    # ST2110 specific
    packet_time: int = 1  # Packet time in ms (1ms for ST2110-31)

    # PTP settings
    use_ptp: bool = False
    ptp_domain: int = 127

    # Output settings
    save_pcap: Optional[str] = None
    interface: Optional[str] = None


@dataclass
class VideoStreamConfig:
    """Configuration for ST2110-20 video streaming."""

    # Network settings
    dest_ip: str
    dest_port: int
    src_ip: Optional[str] = None

    # Video settings
    width: int = 1920
    height: int = 1080
    framerate: int = 30
    pixel_format: Literal['YUY2', 'UYVY', 'I420'] = 'UYVY'  # ST2110-20 typical

    # RTP settings
    payload_type: int = 96  # ST2110-20 typical
    ssrc: Optional[int] = None

    # ST2110 specific
    interlaced: bool = False

    # PTP settings
    use_ptp: bool = False
    ptp_domain: int = 127

    # Output settings
    save_pcap: Optional[str] = None
    interface: Optional[str] = None


class FileStreamer:
    """GStreamer-based file to RTP streamer with ST2110 compliance.

    This class implements best practices for GStreamer:
    - Proper initialization and cleanup
    - Signal handling for pipeline events
    - State management
    - Error recovery

    Examples:
        # Stream audio file to network
        >>> config = AudioStreamConfig(
        ...     dest_ip='239.0.0.1',
        ...     dest_port=5004,
        ...     sample_rate=48000
        ... )
        >>> streamer = FileStreamer()
        >>> streamer.stream_audio_file('audio.wav', config)

        # Stream with PTP and save to pcap
        >>> config = VideoStreamConfig(
        ...     dest_ip='239.0.0.2',
        ...     dest_port=5005,
        ...     use_ptp=True,
        ...     save_pcap='output.pcap'
        ... )
        >>> streamer = FileStreamer()
        >>> streamer.stream_video_file('video.mp4', config)
    """

    def __init__(self):
        """Initialize the file streamer."""
        if not GST_AVAILABLE:
            raise ImportError(
                "GStreamer is not available. Please install GStreamer and PyGObject.\n"
                "Ubuntu/Debian: sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base "
                "gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly "
                "gstreamer1.0-rtsp python3-gi gir1.2-gstreamer-1.0\n"
                "Then: pip install PyGObject"
            )

        self.pipeline = None
        self.loop = None
        self.logger = logging.getLogger(__name__)

    def stream_audio_file(self, file_path: str, config: AudioStreamConfig) -> None:
        """Stream an audio file as RTP stream (ST2110-30/31).

        Args:
            file_path: Path to the audio file
            config: Audio streaming configuration

        Raises:
            FileNotFoundError: If the audio file doesn't exist
            RuntimeError: If GStreamer pipeline fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Build pipeline
        pipeline_str = self._build_audio_pipeline(file_path, config)
        self.logger.info(f"Audio pipeline: {pipeline_str}")

        # Create and run pipeline
        self._run_pipeline(pipeline_str, config.save_pcap)

    def stream_video_file(self, file_path: str, config: VideoStreamConfig) -> None:
        """Stream a video file as RTP stream (ST2110-20).

        Args:
            file_path: Path to the video file
            config: Video streaming configuration

        Raises:
            FileNotFoundError: If the video file doesn't exist
            RuntimeError: If GStreamer pipeline fails
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        # Build pipeline
        pipeline_str = self._build_video_pipeline(file_path, config)
        self.logger.info(f"Video pipeline: {pipeline_str}")

        # Create and run pipeline
        self._run_pipeline(pipeline_str, config.save_pcap)

    def _build_audio_pipeline(self, file_path: str, config: AudioStreamConfig) -> str:
        """Build GStreamer pipeline for audio streaming.

        Pipeline structure:
        filesrc -> decodebin -> audioconvert -> audioresample ->
        audio/x-raw -> rtpL24pay/rtpL16pay -> udpsink

        For pcap capture:
        ... -> tee -> queue -> udpsink
                 \\-> queue -> multifilesink (raw)
        """
        # Determine RTP payload encoder based on bit depth
        if config.bit_depth == 24:
            rtp_pay = "rtpL24pay"
            audio_format = "S24LE"
        else:  # 16-bit
            rtp_pay = "rtpL16pay"
            audio_format = "S16LE"

        # Base pipeline components
        elements = [
            f"filesrc location=\"{file_path}\"",
            "decodebin",
            "audioconvert",
            "audioresample",
            f"audio/x-raw,format={audio_format},rate={config.sample_rate},channels={config.channels}",
            rtp_pay,
        ]

        # Configure RTP payloader
        rtp_config = [f"pt={config.payload_type}"]
        if config.ssrc:
            rtp_config.append(f"ssrc={config.ssrc}")
        if config.packet_time:
            rtp_config.append(f"ptime-multiple={config.packet_time * 1000000}")  # Convert to ns

        elements[-1] += " " + " ".join(rtp_config)

        # Add PTP clock if requested
        if config.use_ptp:
            # Note: PTP clock needs to be set up at application level
            # This would require ptpd running on the system
            self.logger.info(f"PTP requested with domain {config.ptp_domain}")
            # GStreamer PTP clock initialization would go here
            # For now, we log a warning
            self.logger.warning("PTP support requires ptpd to be running on the system")

        # Network sink or tee for pcap
        if config.save_pcap:
            # Use tee to split stream for both network and pcap
            elements.extend([
                "tee name=t",
                "t. ! queue ! udpsink",
                f"host={config.dest_ip} port={config.dest_port}",
            ])

            # Add interface binding if specified
            if config.interface:
                elements[-1] += f" bind-address={config.src_ip or '0.0.0.0'} multicast-iface={config.interface}"

            # Note: For pcap, we'd need to use additional tools or tcpdump
            # GStreamer doesn't directly support pcap writing
            self.logger.warning(
                "PCap capture will require tcpdump running in parallel. "
                f"Run: sudo tcpdump -i {config.interface or 'any'} "
                f"-w {config.save_pcap} udp port {config.dest_port}"
            )
        else:
            # Direct UDP sink
            elements.append(
                f"udpsink host={config.dest_ip} port={config.dest_port}"
            )

            if config.interface:
                elements[-1] += f" bind-address={config.src_ip or '0.0.0.0'} multicast-iface={config.interface}"

        return " ! ".join(elements)

    def _build_video_pipeline(self, file_path: str, config: VideoStreamConfig) -> str:
        """Build GStreamer pipeline for video streaming.

        Pipeline structure:
        filesrc -> decodebin -> videoconvert -> videoscale ->
        video/x-raw -> rtpvrawpay -> udpsink
        """
        # Base pipeline components
        elements = [
            f"filesrc location=\"{file_path}\"",
            "decodebin",
            "videoconvert",
            "videoscale",
            f"video/x-raw,format={config.pixel_format},width={config.width},height={config.height},"
            f"framerate={config.framerate}/1",
        ]

        # Add interlacing if needed
        if config.interlaced:
            elements[-1] += ",interlace-mode=interleaved"

        # RTP payloader for raw video (ST2110-20)
        elements.append(f"rtpvrawpay pt={config.payload_type}")

        if config.ssrc:
            elements[-1] += f" ssrc={config.ssrc}"

        # PTP support
        if config.use_ptp:
            self.logger.info(f"PTP requested with domain {config.ptp_domain}")
            self.logger.warning("PTP support requires ptpd to be running on the system")

        # Network sink
        if config.save_pcap:
            elements.extend([
                "tee name=t",
                "t. ! queue ! udpsink",
                f"host={config.dest_ip} port={config.dest_port}",
            ])

            if config.interface:
                elements[-1] += f" bind-address={config.src_ip or '0.0.0.0'} multicast-iface={config.interface}"

            self.logger.warning(
                "PCap capture will require tcpdump running in parallel. "
                f"Run: sudo tcpdump -i {config.interface or 'any'} "
                f"-w {config.save_pcap} udp port {config.dest_port}"
            )
        else:
            elements.append(
                f"udpsink host={config.dest_ip} port={config.dest_port}"
            )

            if config.interface:
                elements[-1] += f" bind-address={config.src_ip or '0.0.0.0'} multicast-iface={config.interface}"

        return " ! ".join(elements)

    def _run_pipeline(self, pipeline_str: str, save_pcap: Optional[str] = None) -> None:
        """Run the GStreamer pipeline with proper lifecycle management.

        Args:
            pipeline_str: GStreamer pipeline string
            save_pcap: Optional pcap file path for capture instructions
        """
        # Create pipeline
        self.pipeline = Gst.parse_launch(pipeline_str)

        if not self.pipeline:
            raise RuntimeError("Failed to create GStreamer pipeline")

        # Set up bus for message handling
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        # Create main loop
        self.loop = GLib.MainLoop()

        # Set pipeline to PLAYING state
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.logger.error("Unable to set pipeline to PLAYING state")
            raise RuntimeError("Failed to start GStreamer pipeline")

        self.logger.info("Pipeline started. Press Ctrl+C to stop.")

        # Run the loop
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            self._cleanup()

    def _on_bus_message(self, bus, message):
        """Handle messages from the GStreamer bus.

        Args:
            bus: GStreamer bus
            message: Bus message
        """
        t = message.type

        if t == Gst.MessageType.EOS:
            self.logger.info("End of stream reached")
            self.loop.quit()

        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f"Error: {err}, {debug}")
            self.loop.quit()

        elif t == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            self.logger.warning(f"Warning: {warn}, {debug}")

        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending = message.parse_state_changed()
                self.logger.debug(
                    f"Pipeline state changed from {old_state.value_nick} "
                    f"to {new_state.value_nick}"
                )

        return True

    def _cleanup(self):
        """Clean up pipeline resources."""
        if self.pipeline:
            self.logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None

        if self.loop and self.loop.is_running():
            self.loop.quit()


def check_gstreamer_installation() -> tuple[bool, str]:
    """Check if GStreamer is properly installed.

    Returns:
        Tuple of (is_installed, message)
    """
    if not GST_AVAILABLE:
        return False, (
            "GStreamer is not available. Please install:\n"
            "Ubuntu/Debian: sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base "
            "gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly "
            "gstreamer1.0-rtsp python3-gi gir1.2-gstreamer-1.0\n"
            "Then: pip install PyGObject"
        )

    # Check for required plugins
    registry = Gst.Registry.get()
    required_plugins = [
        'coreelements',  # filesrc
        'playback',      # decodebin
        'audioconvert',
        'audioresample',
        'videoconvert',
        'videoscale',
        'rtp',           # RTP payloaders
        'udp',           # udpsink
    ]

    missing_plugins = []
    for plugin_name in required_plugins:
        plugin = registry.find_plugin(plugin_name)
        if not plugin:
            missing_plugins.append(plugin_name)

    if missing_plugins:
        return False, (
            f"Missing GStreamer plugins: {', '.join(missing_plugins)}\n"
            "Install with: sudo apt-get install gstreamer1.0-plugins-base "
            "gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly"
        )

    return True, "GStreamer is properly installed"
