
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

### Capture Network Traffic

Capture packets from a network interface:

```bash
# Capture 20 packets (default)
sudo ttk network capture -i eth0

# Capture specific number of packets
sudo ttk network capture -i eth0 -c 100
```

**Note:** Requires root/sudo privileges.

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
│   ├── cli.py                    # CLI entry point
│   ├── network/
│   │   ├── interfaces.py         # Network interface utilities
│   │   └── packet/
│   │       ├── capture.py        # Packet capture
│   │       └── packet_toolkit.py # Packet manipulation
│   └── custom_headers/
│       └── PTP.py                # PTP protocol headers
├── tests/                        # Test suite
└── pyproject.toml               # Project configuration
```
