#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.prr import generate_prr_collection


@click.command(name="generate-prr-collection")
@click.argument("dataset_config", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False),
    default=None,
    help=(
        "Directory to write the PRR collection tree into "
        "(default: 'prr_output_dir' from the config, else 'prr/<collection_id>')."
    ),
)
def generate_prr_collection_cmd(dataset_config, output_dir):
    """Generate a PRR-style STAC Collection as local files.

    Reads a dataset config (the same YAML used by 'publish') and writes a
    self-contained Collection -> Item -> Assets tree for submission to the
    ESA EarthCODE Project Results Repository.

    Example:
      deep-code generate-prr-collection dataset-config.yaml -o ./prr
    """
    out_dir = generate_prr_collection(dataset_config, output_dir=output_dir)
    click.echo(f"PRR collection written to: {out_dir}")
