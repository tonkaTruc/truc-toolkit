
# Truc Toolkit

A network media QA toolkit for packet capture, analysis, and network interface management.

## Installation

```bash
pip install -e .
```

## Usage

### List Network Interfaces

Display all available network interfaces:

```bash
ttk network list-interfaces
```

Output:
```
lo: ['127.0.0.1', '::1', '00:00:00:00:00:00']
eth0: ['192.168.1.100', 'fe80::a1b2:c3d4:e5f6%eth0', 'aa:bb:cc:dd:ee:ff']
```

### Packet Capture

Capture packets from a network interface:

```bash
# Capture 20 packets (default)
sudo ttk network capture -i eth0

# Capture specific number of packets
sudo ttk network capture -i eth0 -c 100
```

**Note:** Requires root/sudo privileges.

### Pcap File Management

List available pcap files in the cap_store directory:

```bash
ttk network list-pcaps
```

Replay a pcap file on a network interface:

```bash
# Replay all packets
sudo ttk network replay-pcap file.pcap -i eth0

# Replay first 100 packets with 0.1s interval
sudo ttk network replay-pcap file.pcap -i eth0 -c 100 -t 0.1

# Get pcap file info without replaying
ttk network replay-pcap file.pcap -i eth0 --info
```

### Packet Creation

Create and send custom packets:

```bash
# Send a UDP packet
sudo ttk network create-packet -i eth0 --src-ip 192.168.1.100 --dst-ip 192.168.1.1 --dport 5000

# Send a TCP packet with payload
sudo ttk network create-packet -i eth0 --protocol tcp --sport 8080 --dport 80 --payload "Hello"

# Send multiple packets
sudo ttk network create-packet -i eth0 --dst-ip 192.168.1.1 --dport 9999 -c 10
```

**Note:** Requires root/sudo privileges.

### Pcap Modification

Modify packet fields in pcap files:

```bash
# Anonymize source addresses
ttk network modify-pcap input.pcap output.pcap --anonymize

# Zero specific fields
ttk network modify-pcap input.pcap output.pcap --zero-ip-src --zero-mac-src

# Set specific values
ttk network modify-pcap input.pcap output.pcap --ip-src 10.0.0.1 --mac-src 00:11:22:33:44:55
```

### Pcap Inspection

Inspect packets in a pcap file:

```bash
# List all packets
ttk network inspect-pcap file.pcap

# Show detailed info for specific packet
ttk network inspect-pcap file.pcap -n 0 --layers --show-hex
```

### Multicast Group Management

Join and leave multicast groups:

```bash
# Join a multicast group
ttk network mcast-join -i eth0 --group 239.0.0.1

# Join a multicast group and capture 20 packets
sudo ttk network mcast-join -i eth0 --group 239.0.0.1 --capture 20

# Leave a multicast group
ttk network mcast-leave -i eth0 --group 239.0.0.1
```

**Note:** The interface's IPv4 address is automatically detected. Packet capture requires root/sudo privileges. When using `--capture`, the command will automatically leave the multicast group after capturing the specified number of packets.

### Getting Help

```bash
ttk --help              # Main help
ttk network --help      # Network commands help
ttk network capture --help  # Specific command help
```

## Development

For CLI architecture and development guide, see [docs/CLI.md](docs/CLI.md).

### Project Structure

```
toolkit/
├── ttk/
│   ├── cli.py                      # CLI entry point
│   ├── network/
│   │   ├── interfaces.py           # Network interface utilities
│   │   ├── multicast.py            # Multicast group management
│   │   ├── server.py               # Simple TCP server (future)
│   │   └── packet/
│   │       ├── capture.py          # Packet capture
│   │       ├── replay.py           # Pcap replay
│   │       ├── packet_creator.py   # Packet crafting (builder pattern)
│   │       └── packet_modifier.py  # Packet field modification
│   └── custom_headers/
│       └── PTP.py                  # PTP protocol headers
├── Resources/
│   └── cap_store/                  # Pcap file storage
├── tests/                          # Test suite
└── pyproject.toml                  # Project configuration
```
