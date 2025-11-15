# CLI Development Guide

The CLI is built using [Click](https://click.palletsprojects.com/).

## Entry Point

Defined in `pyproject.toml`:

```toml
[project.scripts]
ttk = "ttk.cli:cli"
```

## Command Structure

```
ttk (main group)
└── network (command group)
    ├── list-interfaces (command)
    ├── capture (command)
    ├── list-pcaps (command)
    ├── replay-pcap (command)
    ├── create-packet (command)
    ├── modify-pcap (command)
    ├── inspect-pcap (command)
    ├── multicast-join (command)
    └── multicast-leave (command)
```

## Adding Commands

### Add to Existing Group

```python
@network.command(name="my-command")
@click.option("--param", "-p", help="Parameter description")
def my_command(param):
    """Command description shown in help."""
    click.echo(f"Parameter value: {param}")
```

### Create New Command Group

```python
@cli.group()
def packet():
    """Packet manipulation commands."""
    pass

@packet.command(name="create")
@click.option("--type", "-t", help="Packet type")
def create_packet(type):
    """Create a custom packet."""
    click.echo(f"Creating packet of type: {type}")
```

## Best Practices

**Lazy Imports** - Import heavy dependencies inside functions:

```python
@network.command()
def capture_traffic():
    from ttk.network.packet.capture import PackerCaptor
    # Implementation
```

**Error Handling** - Always catch and display errors:

```python
try:
    # Command implementation
except Exception as e:
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)
```

**Output** - Use `click.echo()` instead of `print()`:

```python
click.echo("Output message")
click.echo("Error message", err=True)
```

## Option Types

```python
@click.option("--text", type=str)                               # String
@click.option("--number", type=int)                             # Integer
@click.option("--flag", is_flag=True)                          # Boolean
@click.option("--choice", type=click.Choice(["a", "b", "c"]))  # Choice
@click.option("--file", type=click.Path(exists=True))          # File path
@click.option("--port", type=click.IntRange(1, 65535))         # Validated int
```

## Useful Patterns

**Environment Variables:**

```python
@click.option("--interface", envvar="TTK_INTERFACE")
```

**Progress Bars:**

```python
with click.progressbar(items, label="Processing") as bar:
    for item in bar:
        # Process item
```

**Colored Output:**

```python
click.echo(click.style("Success!", fg="green"))
click.echo(click.style("Error!", fg="red"))
```

**Testing:**

```python
from click.testing import CliRunner
from ttk.cli import cli

def test_list_interfaces():
    runner = CliRunner()
    result = runner.invoke(cli, ["network", "list-interfaces"])
    assert result.exit_code == 0
```

## Resources

- [Click Documentation](https://click.palletsprojects.com/)
