"""
Command-line interface package

This package contains CLI commands for the federated learning system.
"""

from src.presentation.cli.run_command import run_command, setup_parser

__all__ = [
    'run_command',
    'setup_parser'
] 