"""Command-line interface for the Truc Toolkit."""

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
    """Network-related commands."""
    pass


@network.command(name="list-interfaces")
def list_interfaces():
    """List available network interfaces on this host."""
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
    """Capture network traffic on a specified interface."""
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
