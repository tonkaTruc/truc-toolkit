
# Truc Toolkit

A network media QA toolkit for packet capture, analysis, and network interface management.

## Installation

Install the package in development mode:

```bash
pip install -e .
```

This will install the `ttk` command-line tool and all dependencies.

## CLI Commands

The toolkit provides a unified command-line interface through the `ttk` command:

```bash
ttk --help              # Show main help
ttk --version           # Show version
ttk network --help      # Show network commands help
```

### Network Commands

#### List Network Interfaces

Display all available network interfaces on the host:

```bash
ttk network list-interfaces
```

**Output example:**
```
lo: ['127.0.0.1', '::1', '00:00:00:00:00:00']
eth0: ['192.168.1.100', 'fe80::a1b2:c3d4:e5f6%eth0', 'aa:bb:cc:dd:ee:ff']
```

#### Capture Network Traffic

Capture and display packet summaries from a specified interface:

```bash
ttk network capture -i <interface> [-c <count>]
```

**Options:**
- `-i, --interface TEXT`: Network interface to capture on (required)
- `-c, --count INTEGER`: Number of packets to capture (default: 20)

**Examples:**

```bash
# Capture 20 packets (default) from eth0
sudo ttk network capture -i eth0

# Capture 100 packets from eth0
sudo ttk network capture -i eth0 -c 100

# Show help for capture command
ttk network capture --help
```

**Note:** Packet capture requires root/sudo privileges.

## Migration from Invoke

If you were using the old `invoke` (inv) commands, here's the migration guide:

| Old Command | New Command |
|-------------|-------------|
| `inv list-interfaces` | `ttk network list-interfaces` |
| `inv print-traffic --interface=eth0 --count=20` | `ttk network capture -i eth0 -c 20` |

### Key Improvements

1. **Unified entry point**: All commands are now under the `ttk` command
2. **Better organization**: Commands are grouped (e.g., `network`)
3. **Modern CLI framework**: Using Click instead of invoke
4. **Better help system**: Each command has detailed help via `--help`
5. **Installable**: The `ttk` command is available system-wide after installation

## Development

### Project Structure

```
toolkit/
├── ttk/
│   ├── cli.py                    # Main CLI entry point
│   ├── network/
│   │   ├── interfaces.py         # Network interface utilities
│   │   └── packet/
│   │       ├── capture.py        # Packet capture functionality
│   │       └── packet_toolkit.py # Packet manipulation tools
│   └── custom_headers/
│       └── PTP.py                # PTP protocol headers
├── tests/                        # Test suite
├── pyproject.toml               # Project configuration & dependencies
└── README.md                    # This file
```

### Resources
A collection of packet captures of multi-essence media sources

### Packets
Code to handle packet building, sniffing and inspection

### Sockets
Open different socket types on a host machine 