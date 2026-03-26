#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.lint import LintDataset


@click.command(name="lint-dataset")
@click.argument("dataset_id")
def lint_dataset(dataset_id):
    """Validate metadata of a Zarr dataset before publishing.

    DATASET_ID is the ID of a Zarr dataset in the DeepESDL public or team bucket.
    """
    result = LintDataset(dataset_id=dataset_id).lint_dataset()
    click.echo(result)
