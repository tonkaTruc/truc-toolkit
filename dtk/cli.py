"""Command-line interface for the Dora ToolKit.

Usage:
    dtk --help
    dtk network list-interfaces
    dtk network capture -i eth0
    dtk network list-pcaps
    dtk network replay-pcap ptp_cap.pcap -i eth0
    dtk network create-packet -i eth0
    dtk network modify-pcap input.pcap output.pcap
    dtk network inspect-pcap file.pcap
    dtk network mcast-join -i eth0 --group 239.0.0.1
    dtk network mcast-leave -i eth0 --group 239.0.0.1

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


if __name__ == "__main__":
    cli()
