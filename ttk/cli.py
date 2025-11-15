"""Command-line interface for the Truc Toolkit.

Usage:
    ttk --help
    ttk network list-interfaces
    ttk network capture -i eth0
    ttk network list-pcaps
    ttk network replay-pcap ptp_cap.pcap -i eth0

See docs/CLI.md for development guide.
"""

import os
import sys

import click

from ttk.network.interfaces import create_interfaces_dict


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Truc Toolkit - Network utilities and tools."""
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
def capture_traffic(interface, count):
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
        from ttk.network.packet.capture import PackerCaptor

        click.echo(f"Capturing {count} packets on {interface}...")
        captor = PackerCaptor(capture_int=interface)
        pkts = captor.capture_traffic(count=count)

        click.echo(f"\nCaptured {len(pkts)} packets:\n")
        for pkt in pkts:
            click.echo(pkt.summary())
    except Exception as e:
        click.echo(f"Error capturing traffic: {e}", err=True)
        sys.exit(1)


@network.command(name="list-pcaps")
def list_pcaps():
    """List available pcap files in the cap_store directory."""
    try:
        # Lazy import to avoid scapy dependency issues
        from ttk.network.packet.replay import list_pcaps as get_pcaps

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
        ttk network replay-pcap ptp_cap.pcap -i eth0
        ttk network replay-pcap sync_messages.pcap -i eth0 -l 3
        ttk network replay-pcap /path/to/custom.pcap -i eth0 -c 100

    Requires root/sudo privileges.
    """
    try:
        # Lazy import to avoid scapy dependency issues
        from ttk.network.packet.replay import replay_pcap as do_replay, get_pcap_info

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
        click.echo("\nUse 'ttk network list-pcaps' to see available files.", err=True)
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


if __name__ == "__main__":
    cli()
