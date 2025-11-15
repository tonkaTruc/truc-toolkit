"""Command-line interface for the Truc Toolkit.

This module provides the main CLI entry point for the Truc Toolkit.
Commands are organized into groups (e.g., network) for better organization.

Usage:
    ttk --help                      # Show main help
    ttk network list-interfaces     # List network interfaces
    ttk network capture -i eth0     # Capture packets

For more information, see docs/CLI.md
"""

import os
import sys

import click

from ttk.network.interfaces import create_interfaces_dict


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Truc Toolkit - Network utilities and tools.

    A command-line toolkit for network analysis, packet capture,
    and interface management for media QA workflows.
    """
    pass


@cli.group()
def network():
    """Network-related commands.

    Commands for network interface management and packet analysis.
    """
    pass


@network.command(name="list-interfaces")
def list_interfaces():
    """List available network interfaces on this host.

    Displays all network interfaces with their assigned addresses,
    including IPv4, IPv6, and MAC addresses.

    Example:
        $ ttk network list-interfaces
        lo: ['127.0.0.1', '::1', '00:00:00:00:00:00']
        eth0: ['192.168.1.100', 'fe80::a1b2...', 'aa:bb:cc:dd:ee:ff']
    """
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
    """Capture network traffic on a specified interface.

    Captures packets from the specified network interface and displays
    a summary of each packet. Requires root/sudo privileges to access
    network interfaces.

    \b
    Examples:
        # Capture 20 packets (default) from eth0
        $ sudo ttk network capture -i eth0

        # Capture 100 packets from a specific interface
        $ sudo ttk network capture -i eth0 -c 100

    Note: This command requires root privileges. Run with sudo.
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


if __name__ == "__main__":
    cli()
