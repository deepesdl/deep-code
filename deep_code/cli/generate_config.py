#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.new import TemplateGenerator


@click.command(name="generate-config")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(exists=True, file_okay=False, writable=True),
    default=".",
    help="Output directory for templates",
)
def generate_config(output_dir):
    TemplateGenerator.generate_workflow_template(f"{output_dir}/workflow_config.yaml")
    TemplateGenerator.generate_dataset_template(f"{output_dir}/dataset_config.yaml")
