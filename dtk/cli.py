"""Command-line interface for the Dora ToolKit.

Usage:
    dtk --help

    # Network commands
    dtk network list-interfaces
    dtk network capture -i eth0
    dtk network list-pcaps
    dtk network replay-pcap ptp_cap.pcap -i eth0
    dtk network create-packet -i eth0
    dtk network modify-pcap input.pcap output.pcap
    dtk network inspect-pcap file.pcap
    dtk network mcast-join -i eth0 --group 239.0.0.1
    dtk network mcast-leave -i eth0 --group 239.0.0.1

    # Media commands (SMPTE ST 2110)
    dtk media list-streams capture.pcap
    dtk media export-audio audio.pcap -o output.wav
    dtk media export-video video.pcap -o output.mp4
    dtk media export-anc anc.pcap -o output.json

See docs/CLI.md for development guide.
"""

import os
import sys

import click

from dtk.network.interfaces import create_interfaces_dict


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Dora ToolKit - Network utilities and tools."""
    pass


@cli.group()
def network():
    """Network interface management and packet analysis."""
    pass


@network.command(name="list-interfaces")
def list_interfaces():
    """List available network interfaces with their addresses."""
    try:
        interfaces = create_interfaces_dict()
        if not interfaces:
            click.echo("No network interfaces found.")
            return

        for iface, info in interfaces.items():
            addresses = [x['address'] for x in info['addresses']]
            click.echo(f"{iface}: {addresses}")
    except Exception as e:
        click.echo(f"Error listing interfaces: {e}", err=True)
        sys.exit(1)


@network.command(name="capture")
@click.option(
    "--interface", "-i",
    required=True,
    help="Network interface to capture traffic on"
)
@click.option(
    "--count", "-c",
    default=20,
    type=int,
    help="Number of packets to capture (default: 20)"
)
@click.option(
    "--save", "-s",
    help="Save captured packets to a file in cap_store directory (e.g., 'capture.pcap')"
)
def capture_traffic(interface, count, save):
    """Capture and display packet summaries from a network interface.

    Requires root/sudo privileges.
    """
    if os.geteuid() != 0:
        click.echo(
            "Error: This command requires root privileges to access network interfaces.",
            err=True
        )
        sys.exit(1)

    try:
        # Lazy import to avoid scapy dependency issues when running other commands
        from dtk.network.packet.capture import PackerCaptor

        click.echo(f"Capturing {count} packets on {interface}...")
        captor = PackerCaptor(capture_int=interface)
        pkts = captor.capture_traffic(count=count, save_to=save)

        click.echo(f"\nCaptured {len(pkts)} packets:\n")
        for pkt in pkts:
            click.echo(pkt.summary())

        if save:
            click.echo(f"\nPackets saved to cap_store/{save if save.endswith(('.pcap', '.pcapng')) else save + '.pcap'}")
    except Exception as e:
        click.echo(f"Error capturing traffic: {e}", err=True)
        sys.exit(1)


@network.command(name="list-pcaps")
def list_pcaps():
    """List available pcap files in the cap_store directory."""
    try:
        # Lazy import to avoid scapy dependency issues
        from dtk.network.packet.replay import list_pcaps as get_pcaps

        pcap_files = get_pcaps()

        if not pcap_files:
            click.echo("No pcap files found in cap_store.")
            return

        click.echo(f"Found {len(pcap_files)} pcap file(s) in cap_store:\n")
        for pcap in pcap_files:
            size_mb = pcap['size'] / (1024 * 1024)
            click.echo(f"  {pcap['name']:<50} {size_mb:>8.2f} MB")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error listing pcap files: {e}", err=True)
        sys.exit(1)


@network.command(name="replay-pcap")
@click.argument("pcap_file")
@click.option(
    "--interface", "-i",
    required=True,
    help="Network interface to replay packets on"
)
@click.option(
    "--layer", "-l",
    default=2,
    type=click.Choice(['2', '3']),
    help="OSI layer for replay: 2 (L2 with Ethernet) or 3 (L3 IP only, default: 2)"
)
@click.option(
    "--count", "-c",
    type=int,
    help="Number of packets to replay (default: all packets)"
)
@click.option(
    "--interval", "-t",
    default=0,
    type=float,
    help="Time interval between packets in seconds (default: 0)"
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Suppress verbose output during replay"
)
@click.option(
    "--info",
    is_flag=True,
    help="Show pcap file information without replaying"
)
def replay_pcap(pcap_file, interface, layer, count, interval, quiet, info):
    """Replay a pcap file from cap_store on a network interface.

    PCAP_FILE can be either a filename (e.g., 'ptp_cap.pcap') from the
    cap_store directory, or a full path to any pcap file.

    Examples:
        dtk network replay-pcap ptp_cap.pcap -i eth0
        dtk network replay-pcap sync_messages.pcap -i eth0 -l 3
        dtk network replay-pcap /path/to/custom.pcap -i eth0 -c 100

    Requires root/sudo privileges.
    """
    try:
        # Lazy import to avoid scapy dependency issues
        from dtk.network.packet.replay import replay_pcap as do_replay, get_pcap_info

        # Show info and exit if --info flag is used
        if info:
            pcap_info = get_pcap_info(pcap_file)
            click.echo(f"Pcap file information:")
            click.echo(f"  Name:          {pcap_info['name']}")
            click.echo(f"  Path:          {pcap_info['path']}")
            click.echo(f"  Size:          {pcap_info['size'] / (1024 * 1024):.2f} MB")
            click.echo(f"  Packet count:  {pcap_info['packet_count']}")
            return

        # Check for root privileges for actual replay
        if os.geteuid() != 0:
            click.echo(
                "Error: This command requires root privileges to replay packets.",
                err=True
            )
            sys.exit(1)

        layer_num = int(layer)
        verbose = not quiet

        click.echo(f"Replaying pcap file: {pcap_file}")
        click.echo(f"Interface: {interface}")
        click.echo(f"Layer: L{layer_num}")
        if count:
            click.echo(f"Packet limit: {count}")
        if interval > 0:
            click.echo(f"Inter-packet interval: {interval}s")
        click.echo()

        packet_count = do_replay(
            pcap_file=pcap_file,
            interface=interface,
            layer=layer_num,
            count=count,
            inter=interval,
            verbose=verbose
        )

        click.echo(f"\nSuccessfully replayed {packet_count} packet(s).")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nUse 'dtk network list-pcaps' to see available files.", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied. This command requires root privileges.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error replaying pcap: {e}", err=True)
        sys.exit(1)


@network.command(name="create-packet")
@click.option(
    "--interface", "-i",
    required=True,
    help="Network interface to send packet on"
)
@click.option(
    "--src-mac",
    help="Source MAC address (default: 00:00:00:00:00:00)"
)
@click.option(
    "--dst-mac",
    help="Destination MAC address (default: 00:00:00:00:00:00)"
)
@click.option(
    "--src-ip",
    help="Source IP address"
)
@click.option(
    "--dst-ip",
    help="Destination IP address"
)
@click.option(
    "--protocol",
    type=click.Choice(['udp', 'tcp']),
    default='udp',
    help="Transport protocol (default: udp)"
)
@click.option(
    "--sport",
    type=int,
    help="Source port"
)
@click.option(
    "--dport",
    type=int,
    help="Destination port"
)
@click.option(
    "--payload",
    help="Packet payload (text)"
)
@click.option(
    "--count",
    "-c",
    type=int,
    default=1,
    help="Number of packets to send (default: 1)"
)
@click.option(
    "--layer",
    "-l",
    type=click.Choice(['2', '3']),
    default='2',
    help="OSI layer to send at: 2 (L2 with Ethernet) or 3 (L3 IP only, default: 2)"
)
def create_packet(interface, src_mac, dst_mac, src_ip, dst_ip, protocol, sport, dport, payload, count, layer):
    """Create and send custom packets on a network interface.

    Examples:
        dtk network create-packet -i eth0 --src-ip 192.168.1.100 --dst-ip 192.168.1.1 --dport 5000
        dtk network create-packet -i eth0 --protocol tcp --sport 8080 --dport 80 --payload "Hello"

    Requires root/sudo privileges.
    """
    if os.geteuid() != 0:
        click.echo(
            "Error: This command requires root privileges to send packets.",
            err=True
        )
        sys.exit(1)

    try:
        # Lazy import
        from dtk.network.packet.packet_creator import PacketBuilder
        from scapy.all import sendp, send

        # Build packet
        builder = PacketBuilder(src_mac=src_mac, dst_mac=dst_mac)

        # Add IP layer if specified
        if src_ip or dst_ip:
            builder.add_ip(src=src_ip, dst=dst_ip)

        # Add transport layer
        if protocol == 'udp':
            builder.add_udp(sport=sport, dport=dport)
        elif protocol == 'tcp':
            builder.add_tcp(sport=sport, dport=dport)

        # Add payload if specified
        if payload:
            builder.add_payload(payload)

        packet = builder.build()

        # Display packet info
        click.echo("Packet to send:")
        click.echo(packet.summary())
        click.echo()

        # Send packet
        layer_num = int(layer)
        if layer_num == 2:
            sendp(packet, iface=interface, count=count, verbose=True)
        else:
            send(packet, count=count, verbose=True)

        click.echo(f"\nSuccessfully sent {count} packet(s).")

    except Exception as e:
        click.echo(f"Error creating/sending packet: {e}", err=True)
        sys.exit(1)


@network.command(name="modify-pcap")
@click.argument("input_file")
@click.argument("output_file")
@click.option(
    "--zero-ip-src",
    is_flag=True,
    help="Zero out IP source addresses"
)
@click.option(
    "--zero-ip-dst",
    is_flag=True,
    help="Zero out IP destination addresses"
)
@click.option(
    "--zero-mac-src",
    is_flag=True,
    help="Zero out MAC source addresses"
)
@click.option(
    "--zero-mac-dst",
    is_flag=True,
    help="Zero out MAC destination addresses"
)
@click.option(
    "--anonymize",
    is_flag=True,
    help="Anonymize all source addresses (IP and MAC)"
)
@click.option(
    "--ip-src",
    help="Set IP source address to specific value"
)
@click.option(
    "--ip-dst",
    help="Set IP destination address to specific value"
)
@click.option(
    "--mac-src",
    help="Set MAC source address to specific value"
)
@click.option(
    "--mac-dst",
    help="Set MAC destination address to specific value"
)
def modify_pcap(input_file, output_file, zero_ip_src, zero_ip_dst, zero_mac_src, zero_mac_dst,
                anonymize, ip_src, ip_dst, mac_src, mac_dst):
    """Modify packet fields in a pcap file.

    INPUT_FILE can be a filename from cap_store or a full path.
    OUTPUT_FILE is where the modified pcap will be saved.

    Examples:
        dtk network modify-pcap input.pcap output.pcap --anonymize
        dtk network modify-pcap input.pcap output.pcap --zero-ip-src --zero-mac-src
        dtk network modify-pcap input.pcap output.pcap --ip-src 10.0.0.1 --mac-src 00:11:22:33:44:55
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from dtk.network.packet.packet_modifier import (
            anonymize_packets,
            modify_ip_field,
            modify_ethernet_field,
            save_packets
        )
        from scapy.all import rdpcap

        # Read input file
        try:
            input_path = get_pcap_path(input_file)
        except FileNotFoundError:
            # If not in cap_store, try as direct path
            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")
            input_path = input_file

        packets = rdpcap(str(input_path))
        click.echo(f"Loaded {len(packets)} packets from {input_path}")

        # Apply modifications
        if anonymize:
            packets = anonymize_packets(packets)
            click.echo("Applied anonymization (zeroed IP src and MAC src)")
        else:
            if zero_ip_src or ip_src:
                value = ip_src if ip_src else '0.0.0.0'
                modified, skipped = modify_ip_field(packets, 'src', value)
                click.echo(f"Modified IP src on {modified} packets ({skipped} skipped)")

            if zero_ip_dst or ip_dst:
                value = ip_dst if ip_dst else '0.0.0.0'
                modified, skipped = modify_ip_field(packets, 'dst', value)
                click.echo(f"Modified IP dst on {modified} packets ({skipped} skipped)")

            if zero_mac_src or mac_src:
                value = mac_src if mac_src else '00:00:00:00:00:00'
                modified, skipped = modify_ethernet_field(packets, 'src', value)
                click.echo(f"Modified MAC src on {modified} packets ({skipped} skipped)")

            if zero_mac_dst or mac_dst:
                value = mac_dst if mac_dst else '00:00:00:00:00:00'
                modified, skipped = modify_ethernet_field(packets, 'dst', value)
                click.echo(f"Modified MAC dst on {modified} packets ({skipped} skipped)")

        # Save output
        save_packets(packets, output_file)
        click.echo(f"\nSaved modified pcap to: {output_file}")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error modifying pcap: {e}", err=True)
        sys.exit(1)


@network.command(name="inspect-pcap")
@click.argument("pcap_file")
@click.option(
    "--packet-num",
    "-n",
    type=int,
    help="Show details for a specific packet number (0-indexed)"
)
@click.option(
    "--show-hex",
    is_flag=True,
    help="Show hexdump of packet"
)
@click.option(
    "--layers",
    is_flag=True,
    help="Show layer information"
)
def inspect_pcap(pcap_file, packet_num, show_hex, layers):
    """Inspect packets in a pcap file with detailed information.

    PCAP_FILE can be a filename from cap_store or a full path.

    Examples:
        dtk network inspect-pcap file.pcap
        dtk network inspect-pcap file.pcap -n 0 --show-hex
        dtk network inspect-pcap file.pcap --layers
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from scapy.all import rdpcap, hexdump

        # Read pcap file
        try:
            pcap_path = get_pcap_path(pcap_file)
        except FileNotFoundError:
            if not os.path.exists(pcap_file):
                raise FileNotFoundError(f"Pcap file not found: {pcap_file}")
            pcap_path = pcap_file

        packets = rdpcap(str(pcap_path))

        click.echo(f"Pcap file: {pcap_path}")
        click.echo(f"Total packets: {len(packets)}\n")

        if packet_num is not None:
            # Show specific packet
            if packet_num < 0 or packet_num >= len(packets):
                click.echo(f"Error: Packet number {packet_num} out of range (0-{len(packets)-1})", err=True)
                sys.exit(1)

            pkt = packets[packet_num]
            click.echo(f"=== Packet {packet_num} ===")
            click.echo(f"Summary: {pkt.summary()}")
            click.echo()

            if layers:
                click.echo("Layers:")
                pkt.show()
                click.echo()

            if show_hex:
                click.echo("Hexdump:")
                hexdump(pkt)
        else:
            # Show summary of all packets
            for i, pkt in enumerate(packets):
                click.echo(f"{i:4d}: {pkt.summary()}")

            if layers or show_hex:
                click.echo("\nNote: Use -n <packet_num> to show detailed layer/hex info for a specific packet")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error inspecting pcap: {e}", err=True)
        sys.exit(1)


@network.command(name="mcast-join")
@click.option(
    "--interface", "-i",
    required=True,
    help="Network interface name (e.g., eth0)"
)
@click.option(
    "--group", "-g",
    required=True,
    help="Multicast group IP address to join (e.g., 239.0.0.1)"
)
@click.option(
    "--capture", "-c",
    type=int,
    help="Number of packets to capture after joining (requires root)"
)
@click.option(
    "--save", "-s",
    help="Save captured packets to a file in cap_store directory (e.g., 'mcast_capture.pcap'). Requires --capture."
)
def mcast_join(interface, group, capture, save):
    """Join a multicast group and optionally capture packets.

    Examples:
        dtk network mcast-join -i eth0 --group 239.0.0.1
        dtk network mcast-join -i eth0 --group 239.0.0.1 --capture 20
        dtk network mcast-join -i eth0 --group 239.0.0.1 --capture 20 --save mcast.pcap

    Note: Packet capture requires root/sudo privileges.
    """
    # Validate save option
    if save and not capture:
        click.echo(
            "Error: --save option requires --capture to be specified.",
            err=True
        )
        sys.exit(1)

    # Check for root if capture is requested
    if capture and os.geteuid() != 0:
        click.echo(
            "Error: Packet capture requires root privileges.",
            err=True
        )
        sys.exit(1)

    try:
        # Lazy imports
        from dtk.network.multicast import MulticastMgr
        from dtk.network.interfaces import get_interface_ip

        # Get the IPv4 address for the interface
        try:
            local_ip = get_interface_ip(interface)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("\nUse 'dtk network list-interfaces' to see available interfaces.", err=True)
            sys.exit(1)

        click.echo(f"Using interface {interface} ({local_ip})")
        click.echo(f"Joining multicast group {group}...")

        # Create multicast manager
        mcast_mgr = MulticastMgr(switch_ip=local_ip)

        # Join the multicast group
        mcast_mgr.join(group)
        click.echo(f"Successfully joined multicast group {group}")

        # If capture is requested, capture packets
        if capture:
            from dtk.network.packet.capture import PackerCaptor

            click.echo(f"\nCapturing {capture} packets on {interface}...")
            captor = PackerCaptor(capture_int=interface)
            pkts = captor.capture_traffic(count=capture, save_to=save)

            click.echo(f"\nCaptured {len(pkts)} packets:\n")
            for pkt in pkts:
                click.echo(pkt.summary())

            if save:
                click.echo(f"\nPackets saved to cap_store/{save if save.endswith(('.pcap', '.pcapng')) else save + '.pcap'}")

            # Leave the multicast group after capture
            click.echo(f"\nLeaving multicast group {group}...")
            mcast_mgr.leave(group)
            click.echo(f"Successfully left multicast group {group}")
        else:
            click.echo("\nNote: The multicast group membership will remain active.")
            click.echo(f"Use 'dtk network mcast-leave -i {interface} --group {group}' to leave.")

    except Exception as e:
        click.echo(f"Error with multicast operation: {e}", err=True)
        sys.exit(1)


@network.command(name="mcast-leave")
@click.option(
    "--interface", "-i",
    required=True,
    help="Network interface name (e.g., eth0)"
)
@click.option(
    "--group", "-g",
    required=True,
    help="Multicast group IP address to leave (e.g., 239.0.0.1)"
)
def mcast_leave(interface, group):
    """Leave a multicast group.

    Examples:
        dtk network mcast-leave -i eth0 --group 239.0.0.1
    """
    try:
        # Lazy imports
        from dtk.network.multicast import MulticastMgr
        from dtk.network.interfaces import get_interface_ip

        # Get the IPv4 address for the interface
        try:
            local_ip = get_interface_ip(interface)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            click.echo("\nUse 'dtk network list-interfaces' to see available interfaces.", err=True)
            sys.exit(1)

        click.echo(f"Using interface {interface} ({local_ip})")
        click.echo(f"Leaving multicast group {group}...")

        # Create multicast manager
        mcast_mgr = MulticastMgr(switch_ip=local_ip)

        # Leave the multicast group
        mcast_mgr.leave(group)
        click.echo(f"Successfully left multicast group {group}")

    except Exception as e:
        click.echo(f"Error leaving multicast group: {e}", err=True)
        sys.exit(1)


@cli.group()
def media():
    """SMPTE ST 2110 media extraction and export commands."""
    pass


@media.command(name="list-streams")
@click.argument("pcap_file")
@click.option(
    "--use-ptp",
    is_flag=True,
    help="Extract and display PTP timing information"
)
def list_streams(pcap_file, use_ptp):
    """List all RTP streams in a pcap file.

    PCAP_FILE can be a filename from cap_store or a full path.

    Examples:
        dtk media list-streams audio_capture.pcap
        dtk media list-streams video_capture.pcap --use-ptp
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from dtk.media.rtp_extractor import RTPStreamExtractor

        # Get pcap path
        try:
            pcap_path = get_pcap_path(pcap_file)
        except FileNotFoundError:
            if not os.path.exists(pcap_file):
                raise FileNotFoundError(f"Pcap file not found: {pcap_file}")
            pcap_path = pcap_file

        click.echo(f"Analyzing pcap file: {pcap_path}")
        if use_ptp:
            click.echo("PTP timing extraction enabled")
        click.echo()

        # Extract streams
        extractor = RTPStreamExtractor(use_ptp=use_ptp)
        extractor.extract_from_pcap(str(pcap_path))

        streams = extractor.list_streams()

        if not streams:
            click.echo("No RTP streams found in pcap file.")
            return

        click.echo(f"Found {len(streams)} RTP stream(s):\n")

        for ssrc, info in streams:
            click.echo(f"SSRC: {ssrc:#010x}")
            click.echo(f"  Payload Type: {info.payload_type} ({extractor.get_payload_type_name(info.payload_type)})")
            click.echo(f"  Packets: {info.packet_count}")
            click.echo(f"  Sequence: {info.first_seq} -> {info.last_seq}")
            click.echo(f"  Timestamp Range: {info.first_timestamp} -> {info.last_timestamp}")
            click.echo(f"  Duration: {info.duration:.3f}s")
            click.echo(f"  Packets Lost: {info.packets_lost} ({info.packet_loss_rate:.2f}%)")
            click.echo(f"  Out of Order: {info.packets_out_of_order}")
            if use_ptp and info.has_ptp:
                click.echo(f"  PTP Timing: Available")
            click.echo()

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error analyzing pcap: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@media.command(name="export-audio")
@click.argument("pcap_file")
@click.option(
    "--output", "-o",
    required=True,
    help="Output audio file path"
)
@click.option(
    "--format", "-f",
    type=click.Choice(['wav', 'flac', 'mp3'], case_sensitive=False),
    default='wav',
    help="Output format (default: wav)"
)
@click.option(
    "--ssrc",
    type=str,
    help="SSRC of stream to export (hex, e.g., 0x12345678). If not specified, exports first audio stream."
)
@click.option(
    "--sample-rate",
    type=int,
    help="Sample rate in Hz (auto-detect if not specified)"
)
@click.option(
    "--bit-depth",
    type=click.Choice(['16', '24'], case_sensitive=False),
    help="Bit depth for output (auto-detect if not specified)"
)
@click.option(
    "--channels",
    type=int,
    help="Number of audio channels (auto-detect if not specified)"
)
@click.option(
    "--use-ptp",
    is_flag=True,
    help="Use PTP timestamps for timing"
)
@click.option(
    "--bitrate",
    type=int,
    default=320,
    help="Bitrate for MP3 export in kbps (default: 320)"
)
def export_audio(pcap_file, output, format, ssrc, sample_rate, bit_depth, channels, use_ptp, bitrate):
    """Export ST 2110-30 audio stream to audio file.

    Examples:
        dtk media export-audio audio.pcap -o output.wav
        dtk media export-audio audio.pcap -o output.flac --format flac
        dtk media export-audio audio.pcap -o output.mp3 --format mp3 --bitrate 320
        dtk media export-audio audio.pcap -o output.wav --ssrc 0x12345678 --use-ptp
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from dtk.media.rtp_extractor import RTPStreamExtractor
        from dtk.media.decoders import ST211030Decoder
        from dtk.media.decoders.st2110_30 import AudioStreamParams
        from dtk.media.exporters import AudioExporter

        # Get pcap path
        try:
            pcap_path = get_pcap_path(pcap_file)
        except FileNotFoundError:
            if not os.path.exists(pcap_file):
                raise FileNotFoundError(f"Pcap file not found: {pcap_file}")
            pcap_path = pcap_file

        click.echo(f"Processing pcap file: {pcap_path}")

        # Extract streams
        extractor = RTPStreamExtractor(use_ptp=use_ptp)
        extractor.extract_from_pcap(str(pcap_path))

        # Determine which stream to export
        target_ssrc = None
        if ssrc:
            # Parse SSRC (supports hex format)
            target_ssrc = int(ssrc, 16) if ssrc.startswith('0x') else int(ssrc)
            if target_ssrc not in extractor.streams:
                click.echo(f"Error: SSRC {ssrc} not found in pcap", err=True)
                click.echo("\nAvailable streams:", err=True)
                for s, info in extractor.list_streams():
                    click.echo(f"  {s:#010x} - {extractor.get_payload_type_name(info.payload_type)}", err=True)
                sys.exit(1)
        else:
            # Find first audio stream (PT 97 is common for ST 2110-30)
            for s, info in extractor.list_streams():
                if info.payload_type == 97 or 'Audio' in extractor.get_payload_type_name(info.payload_type):
                    target_ssrc = s
                    break

            if target_ssrc is None:
                # Just use first stream
                if extractor.streams:
                    target_ssrc = list(extractor.streams.keys())[0]
                else:
                    click.echo("Error: No RTP streams found", err=True)
                    sys.exit(1)

        stream_info = extractor.stream_info[target_ssrc]
        packets = extractor.streams[target_ssrc]

        click.echo(f"Exporting stream SSRC {target_ssrc:#010x}")
        click.echo(f"  Payload Type: {stream_info.payload_type}")
        click.echo(f"  Packets: {stream_info.packet_count}")
        click.echo()

        # Set up decoder parameters if specified
        params = None
        if sample_rate or bit_depth or channels:
            params = AudioStreamParams(
                sample_rate=sample_rate or 48000,
                bit_depth=int(bit_depth) if bit_depth else 24,
                channels=channels or 2
            )

        # Decode audio
        click.echo("Decoding audio stream...")
        decoder = ST211030Decoder(params=params)
        samples = decoder.decode(packets, stream_info)

        audio_info = decoder.get_audio_info()
        click.echo(f"  Sample Rate: {audio_info['sample_rate']} Hz")
        click.echo(f"  Bit Depth: {audio_info['bit_depth']} bits")
        click.echo(f"  Channels: {audio_info['channels']}")
        click.echo(f"  Duration: {audio_info['duration_formatted']}")
        click.echo()

        # Export audio
        click.echo(f"Exporting to {format.upper()}...")
        exporter = AudioExporter()
        output_path = exporter.export(
            samples=samples,
            sample_rate=audio_info['sample_rate'],
            output_path=output,
            format=format,
            bit_depth=int(bit_depth) if bit_depth else audio_info['bit_depth'],
            bitrate=bitrate
        )

        click.echo(f"Successfully exported audio to: {output_path}")

    except ImportError as e:
        if 'soundfile' in str(e) and format == 'flac':
            click.echo("Error: FLAC export requires the soundfile package.", err=True)
            click.echo("Install with: pip install soundfile", err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error exporting audio: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@media.command(name="export-video")
@click.argument("pcap_file")
@click.option(
    "--output", "-o",
    required=True,
    help="Output video file path"
)
@click.option(
    "--format", "-f",
    type=click.Choice(['mp4', 'mov', 'avi', 'mkv'], case_sensitive=False),
    default='mp4',
    help="Output format (default: mp4)"
)
@click.option(
    "--codec", "-c",
    type=click.Choice(['h264', 'h265', 'prores', 'prores_ks'], case_sensitive=False),
    default='h264',
    help="Video codec (default: h264)"
)
@click.option(
    "--ssrc",
    type=str,
    help="SSRC of stream to export (hex). If not specified, exports first video stream."
)
@click.option(
    "--crf",
    type=int,
    default=18,
    help="Quality for H.264/H.265 (0-51, lower is better, default: 18)"
)
@click.option(
    "--preset",
    type=click.Choice(['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']),
    default='medium',
    help="Encoding speed preset for H.264/H.265 (default: medium)"
)
@click.option(
    "--prores-profile",
    type=click.Choice(['proxy', 'lt', 'standard', 'hq', '4444', '4444xq']),
    default='standard',
    help="ProRes profile (default: standard)"
)
@click.option(
    "--use-ptp",
    is_flag=True,
    help="Use PTP timestamps for timing"
)
def export_video(pcap_file, output, format, codec, ssrc, crf, preset, prores_profile, use_ptp):
    """Export ST 2110-20 video stream to video file.

    Examples:
        dtk media export-video video.pcap -o output.mp4
        dtk media export-video video.pcap -o output.mov --codec prores
        dtk media export-video video.pcap -o output.mp4 --codec h265 --crf 20
        dtk media export-video video.pcap -o output.mov --ssrc 0xabcdef --use-ptp
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from dtk.media.rtp_extractor import RTPStreamExtractor
        from dtk.media.decoders import ST211020Decoder
        from dtk.media.exporters import VideoExporter

        # Check if FFmpeg is available
        if not VideoExporter.check_ffmpeg():
            click.echo("Error: FFmpeg is not installed or not accessible.", err=True)
            click.echo("Please install FFmpeg to export video.", err=True)
            sys.exit(1)

        # Get pcap path
        try:
            pcap_path = get_pcap_path(pcap_file)
        except FileNotFoundError:
            if not os.path.exists(pcap_file):
                raise FileNotFoundError(f"Pcap file not found: {pcap_file}")
            pcap_path = pcap_file

        click.echo(f"Processing pcap file: {pcap_path}")

        # Extract streams
        extractor = RTPStreamExtractor(use_ptp=use_ptp)
        extractor.extract_from_pcap(str(pcap_path))

        # Determine which stream to export
        target_ssrc = None
        if ssrc:
            target_ssrc = int(ssrc, 16) if ssrc.startswith('0x') else int(ssrc)
            if target_ssrc not in extractor.streams:
                click.echo(f"Error: SSRC {ssrc} not found in pcap", err=True)
                sys.exit(1)
        else:
            # Find first video stream (PT 96 is common for ST 2110-20)
            for s, info in extractor.list_streams():
                if info.payload_type == 96 or 'Video' in extractor.get_payload_type_name(info.payload_type):
                    target_ssrc = s
                    break

            if target_ssrc is None and extractor.streams:
                target_ssrc = list(extractor.streams.keys())[0]

        if target_ssrc is None:
            click.echo("Error: No RTP streams found", err=True)
            sys.exit(1)

        stream_info = extractor.stream_info[target_ssrc]
        packets = extractor.streams[target_ssrc]

        click.echo(f"Exporting stream SSRC {target_ssrc:#010x}")
        click.echo(f"  Payload Type: {stream_info.payload_type}")
        click.echo(f"  Packets: {stream_info.packet_count}")
        click.echo()

        # Decode video
        click.echo("Decoding video stream...")
        decoder = ST211020Decoder()
        frames = decoder.decode(packets, stream_info)

        if not frames:
            click.echo("Error: No video frames decoded", err=True)
            sys.exit(1)

        video_info = decoder.get_video_info()
        click.echo(f"  Resolution: {video_info['resolution']}")
        click.echo(f"  Pixel Format: {video_info['pixel_format']}")
        click.echo(f"  Frame Rate: {video_info['frame_rate']} fps")
        click.echo(f"  Frames: {video_info['num_frames']}")
        click.echo(f"  Duration: {video_info['duration_seconds']:.3f}s")
        click.echo()

        # Export video
        click.echo(f"Encoding to {format.upper()} with {codec.upper()}...")
        exporter = VideoExporter()
        output_path = exporter.export(
            frames=frames,
            frame_rate=video_info['frame_rate'],
            output_path=output,
            format=format,
            codec=codec,
            crf=crf,
            preset=preset,
            prores_profile=prores_profile,
            pixel_format='yuv422' if video_info['pixel_format'] == 'YCbCr-4:2:2' else 'rgb'
        )

        click.echo(f"Successfully exported video to: {output_path}")

    except Exception as e:
        click.echo(f"Error exporting video: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@media.command(name="export-anc")
@click.argument("pcap_file")
@click.option(
    "--output", "-o",
    required=True,
    help="Output file path"
)
@click.option(
    "--format", "-f",
    type=click.Choice(['srt', 'vtt', 'csv', 'json', 'txt'], case_sensitive=False),
    default='json',
    help="Output format (default: json)"
)
@click.option(
    "--type", "-t",
    type=click.Choice(['captions', 'timecode', 'all'], case_sensitive=False),
    default='all',
    help="Type of ancillary data to export (default: all)"
)
@click.option(
    "--ssrc",
    type=str,
    help="SSRC of stream to export (hex). If not specified, exports first ancillary stream."
)
@click.option(
    "--use-ptp",
    is_flag=True,
    help="Use PTP timestamps for timing"
)
def export_anc(pcap_file, output, format, type, ssrc, use_ptp):
    """Export ST 2110-40 ancillary data to various formats.

    Examples:
        dtk media export-anc anc.pcap -o output.json
        dtk media export-anc anc.pcap -o captions.srt --type captions --format srt
        dtk media export-anc anc.pcap -o timecode.csv --type timecode --format csv
        dtk media export-anc anc.pcap -o anc_data.txt --format txt --use-ptp
    """
    try:
        # Lazy imports
        from dtk.network.packet.replay import get_pcap_path
        from dtk.media.rtp_extractor import RTPStreamExtractor
        from dtk.media.decoders import ST211040Decoder
        from dtk.media.exporters import AncillaryExporter

        # Get pcap path
        try:
            pcap_path = get_pcap_path(pcap_file)
        except FileNotFoundError:
            if not os.path.exists(pcap_file):
                raise FileNotFoundError(f"Pcap file not found: {pcap_file}")
            pcap_path = pcap_file

        click.echo(f"Processing pcap file: {pcap_path}")

        # Extract streams
        extractor = RTPStreamExtractor(use_ptp=use_ptp)
        extractor.extract_from_pcap(str(pcap_path))

        # Determine which stream to export
        target_ssrc = None
        if ssrc:
            target_ssrc = int(ssrc, 16) if ssrc.startswith('0x') else int(ssrc)
            if target_ssrc not in extractor.streams:
                click.echo(f"Error: SSRC {ssrc} not found in pcap", err=True)
                sys.exit(1)
        else:
            # Find first ancillary stream (PT 98 is common for ST 2110-40)
            for s, info in extractor.list_streams():
                if info.payload_type == 98 or 'Ancillary' in extractor.get_payload_type_name(info.payload_type):
                    target_ssrc = s
                    break

            if target_ssrc is None and extractor.streams:
                target_ssrc = list(extractor.streams.keys())[0]

        if target_ssrc is None:
            click.echo("Error: No RTP streams found", err=True)
            sys.exit(1)

        stream_info = extractor.stream_info[target_ssrc]
        packets = extractor.streams[target_ssrc]

        click.echo(f"Exporting stream SSRC {target_ssrc:#010x}")
        click.echo(f"  Payload Type: {stream_info.payload_type}")
        click.echo(f"  Packets: {stream_info.packet_count}")
        click.echo()

        # Decode ancillary data
        click.echo("Decoding ancillary data...")
        decoder = ST211040Decoder()
        anc_packets = decoder.decode(packets, stream_info)

        click.echo(f"  ANC Packets: {len(anc_packets)}")
        click.echo(f"  Timecodes: {len(decoder.timecodes)}")
        click.echo(f"  Captions: {len(decoder.captions)}")

        # Show summary
        summary = decoder.get_anc_summary()
        if summary:
            click.echo("\n  ANC Packet Types:")
            for pkt_type, count in summary.items():
                click.echo(f"    {pkt_type}: {count}")
        click.echo()

        # Export based on type
        exporter = AncillaryExporter()

        if type == 'captions':
            if not decoder.captions:
                click.echo("Warning: No captions found in stream", err=True)
            if format not in ['srt', 'vtt']:
                click.echo(f"Error: Format {format} not supported for captions. Use srt or vtt.", err=True)
                sys.exit(1)
            output_path = exporter.export_captions(decoder.captions, output, format)

        elif type == 'timecode':
            if not decoder.timecodes:
                click.echo("Warning: No timecode data found in stream", err=True)
            if format not in ['csv', 'txt', 'json']:
                click.echo(f"Error: Format {format} not supported for timecode. Use csv, txt, or json.", err=True)
                sys.exit(1)
            output_path = exporter.export_timecode(decoder.timecodes, output, format)

        else:  # all
            output_path = exporter.export_anc_packets(anc_packets, output, format)

        click.echo(f"Successfully exported ancillary data to: {output_path}")

    except Exception as e:
        click.echo(f"Error exporting ancillary data: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
