"""
Command-line interface entry point

This module provides the entry point for the CLI command.
"""
import sys
from src.presentation.cli.run_command import run_command, setup_parser

if __name__ == '__main__':
    parser = setup_parser()
    args = parser.parse_args()
    sys.exit(run_command(args)) 