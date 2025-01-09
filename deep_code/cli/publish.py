#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.publish import DatasetPublisher


@click.command(name="publish-dataset")
@click.option(
    "--dataset-config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the dataset-config.yaml file with dataset information.",
)
def publish_dataset(dataset_config):
    """Request publishing a dataset to the open science catalogue.
    """
    publisher = DatasetPublisher()
    publisher.publish_dataset(dataset_config_path=dataset_config)
