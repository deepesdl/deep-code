#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.cli.generate_config import generate_config
from deep_code.cli.publish import publish


@click.group()
def main():
    """Deep Code CLI."""
    pass


main.add_command(publish)
main.add_command(generate_config)

if __name__ == "__main__":
    main()
