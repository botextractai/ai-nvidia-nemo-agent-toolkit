#!/usr/bin/env python3
"""
Environment Setup Script

This script loads environment variables from a .env file and makes them available
as system environment variables. It is designed to work on Microsoft Windows, Linux, and Apple macOS.

Usage:
    # Load environment variables and run a command
    python env_setup.py your_command_here
    
    # Or source it in your shell (Linux/Apple macOS)
    source <(python env_setup.py --export)
    
    # Or use it in PowerShell (Microsoft Windows)
    python env_setup.py --export | ForEach-Object { Invoke-Expression $_ }

Alternatively, you can import this module in Python:
    from env_setup import load_env
    load_env()
"""
import sys
import subprocess
from pathlib import Path

# Try to import python-dotenv
try:
    from dotenv import load_dotenv, dotenv_values
except ImportError:
    print("⚠️  Error: python-dotenv is not installed.", file=sys.stderr)
    print("   Install it with: pip install python-dotenv", file=sys.stderr)
    sys.exit(1)


def find_env_file():
    """Find the .env file in the project root."""
    # Start from the directory containing this script (project root)
    current = Path(__file__).parent
    env_file = current / ".env"
    
    # Check if .env exists in the current directory
    if env_file.exists():
        return env_file
    
    # Walk up the directory tree looking for .env or pyproject.toml
    for parent in [current] + list(current.parents):
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
        # Also check for pyproject.toml as a project root indicator
        if (parent / "pyproject.toml").exists():
            env_file = parent / ".env"
            if env_file.exists():
                return env_file
    
    return None


def load_env(env_file=None, override=False):
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file. If None, will search for it.
        override: If True, override existing environment variables.
                  If False, only set variables that don't already exist.
    
    Returns:
        dict: Dictionary of loaded environment variables
    """
    if env_file is None:
        env_file = find_env_file()
    
    if env_file is None:
        print("⚠️  Warning: .env file not found", file=sys.stderr)
        print(f"   Searched from: {Path(__file__).parent}", file=sys.stderr)
        return {}
    
    if not env_file.exists():
        print(f"⚠️  Warning: .env file does not exist: {env_file}", file=sys.stderr)
        return {}
    
    # Load .env file
    if override:
        # Override existing variables
        load_dotenv(env_file, override=True)
    else:
        # Don't override existing variables
        load_dotenv(env_file, override=False)
    
    # Get all values from .env file
    env_vars = dotenv_values(env_file)
    
    # Filter out None values (comments, empty lines)
    env_vars = {k: v for k, v in env_vars.items() if v is not None}
    
    return env_vars


def export_env_vars(env_vars):
    """
    Export environment variables in a format suitable for shell sourcing.
    
    Args:
        env_vars: Dictionary of environment variables
    
    Returns:
        str: Shell commands to export variables
    """
    lines = []
    for key, value in env_vars.items():
        # Escape special characters in the value
        if sys.platform == "win32":
            # Microsoft Windows PowerShell/CMD format
            # Escape quotes and special characters
            escaped_value = str(value).replace('"', '\\"').replace('$', '`$')
            lines.append(f'$env:{key}="{escaped_value}"')
        else:
            # Unix/Linux/Apple macOS format
            # Escape quotes, dollar signs, and backticks
            escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
            lines.append(f'export {key}="{escaped_value}"')
    
    return '\n'.join(lines)


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load environment variables from .env file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load env and run a command
  python env_setup.py python your_script.py
  
  # Export variables for shell (Linux/Apple macOS)
  source <(python env_setup.py --export)
  
  # Export variables for PowerShell (Microsoft Windows)
  python env_setup.py --export | ForEach-Object { Invoke-Expression $_ }
        """
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        help='Print export commands instead of executing a command'
    )
    
    parser.add_argument(
        '--override',
        action='store_true',
        help='Override existing environment variables'
    )
    
    parser.add_argument(
        '--env-file',
        type=Path,
        help='Path to .env file (default: search for .env in project root)'
    )
    
    parser.add_argument(
        'command',
        nargs=argparse.REMAINDER,
        help='Command to execute after loading environment variables'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    env_vars = load_env(env_file=args.env_file, override=args.override)
    
    if args.export:
        # Export mode: print export commands
        print(export_env_vars(env_vars))
        return 0
    
    if args.command:
        # Execute command with loaded environment
        try:
            # Execute the command
            result = subprocess.run(args.command, check=False)
            return result.returncode
        except FileNotFoundError:
            print(f"❌ Error: Command not found: {args.command[0]}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ Error executing command: {e}", file=sys.stderr)
            return 1
    else:
        # No command provided, just load the environment
        # This is useful when importing the module
        if env_vars:
            print(f"✅ Loaded {len(env_vars)} environment variable(s) from .env file")
        return 0


if __name__ == "__main__":
    sys.exit(main())
