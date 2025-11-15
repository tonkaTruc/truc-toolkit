# CLI Architecture and Development Guide

## Overview

The Truc Toolkit CLI is built using [Click](https://click.palletsprojects.com/), a Python package for creating command-line interfaces with minimal code.

## Architecture

### Entry Point

The CLI is defined in `ttk/cli.py` and registered as a console script in `pyproject.toml`:

```toml
[project.scripts]
ttk = "ttk.cli:cli"
```

This creates the `ttk` command when the package is installed.

### Command Structure

Commands are organized hierarchically:

```
ttk (main group)
└── network (command group)
    ├── list-interfaces (command)
    └── capture (command)
```

### Command Groups

Command groups allow organizing related commands together. They're defined using `@click.group()`:

```python
@click.group()
def network():
    """Network-related commands."""
    pass
```

### Commands

Individual commands are added to groups using decorators:

```python
@network.command(name="list-interfaces")
def list_interfaces():
    """List available network interfaces on this host."""
    # Implementation
```

## Adding New Commands

### 1. Simple Command

To add a new command to an existing group:

```python
@network.command(name="my-command")
@click.option("--param", "-p", help="Parameter description")
def my_command(param):
    """Command description shown in help."""
    click.echo(f"Parameter value: {param}")
```

### 2. New Command Group

To create a new command group:

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

### 1. Lazy Imports

Import heavy dependencies (like Scapy) inside command functions to keep the CLI responsive:

```python
@network.command()
def capture_traffic():
    # Lazy import - only loaded when this command is run
    from ttk.network.packet.capture import PackerCaptor
    # Implementation
```

### 2. Error Handling

Use try-except blocks and provide clear error messages:

```python
@network.command()
def my_command():
    try:
        # Command implementation
        pass
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
```

### 3. Options and Arguments

- **Options** (--flag): Optional parameters with defaults
- **Arguments**: Required positional parameters

```python
@network.command()
@click.argument("interface")  # Required positional argument
@click.option("--count", "-c", default=10, help="Number of items")
def example(interface, count):
    """Example command with argument and option."""
    pass
```

### 4. Help Text

Provide comprehensive help text:

```python
@network.command(name="my-command")
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output with detailed information"
)
def my_command(verbose):
    """
    Detailed command description.

    This can be multiple lines and will appear when
    users run: ttk network my-command --help
    """
    pass
```

### 5. Output

Use `click.echo()` instead of `print()`:

```python
# Good
click.echo("Output message")
click.echo("Error message", err=True)

# Avoid
print("Output message")
```

## Option Types

Click supports various option types:

```python
@click.command()
@click.option("--text", type=str)           # String
@click.option("--number", type=int)         # Integer
@click.option("--decimal", type=float)      # Float
@click.option("--flag", is_flag=True)       # Boolean flag
@click.option("--choice", type=click.Choice(["a", "b", "c"]))  # Choice
@click.option("--file", type=click.Path(exists=True))          # File path
def example_command(**kwargs):
    pass
```

## Validation

Add custom validation:

```python
@click.command()
@click.option("--port", type=click.IntRange(1, 65535))
def server(port):
    """Start server on specified port."""
    pass
```

## Environment Variables

Click can read from environment variables:

```python
@click.option(
    "--interface",
    envvar="TTK_INTERFACE",
    help="Network interface (env: TTK_INTERFACE)"
)
```

## Testing Commands

Test CLI commands using Click's testing utilities:

```python
from click.testing import CliRunner
from ttk.cli import cli

def test_list_interfaces():
    runner = CliRunner()
    result = runner.invoke(cli, ["network", "list-interfaces"])
    assert result.exit_code == 0
    assert "lo" in result.output
```

## Common Patterns

### Confirmation Prompts

```python
@click.command()
@click.confirmation_option(prompt="Are you sure?")
def dangerous_operation():
    """Perform a dangerous operation."""
    pass
```

### Progress Bars

```python
import click

@click.command()
def process_data():
    items = range(100)
    with click.progressbar(items, label="Processing") as bar:
        for item in bar:
            # Process item
            pass
```

### Colored Output

```python
click.echo(click.style("Success!", fg="green"))
click.echo(click.style("Warning!", fg="yellow"))
click.echo(click.style("Error!", fg="red"))
```

## Debugging

Run commands with verbose exception traces:

```python
if __name__ == "__main__":
    cli()  # Normal mode
    # cli(obj={})  # Debug mode - shows full tracebacks
```

## Resources

- [Click Documentation](https://click.palletsprojects.com/)
- [Click API Reference](https://click.palletsprojects.com/en/8.1.x/api/)
- [Click Examples](https://github.com/pallets/click/tree/main/examples)
