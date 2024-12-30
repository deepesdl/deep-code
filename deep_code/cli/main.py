#!/usr/bin/env python3

# Copyright (c) 2024 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.cli.publish import publish_product


@click.group()
def main():
    """Deep Code CLI."""
    pass


main.add_command(publish_product)
if __name__ == "__main__":
    main()
