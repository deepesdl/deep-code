#!/usr/bin/env python3

# Copyright (c) 2024 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.api.publish import ProductPublisher


@click.command(name="publish-product")
@click.option(
    "--git-config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the git.yaml file with GitHub credentials.",
)
@click.option(
    "--dataset-config",
    required=True,
    type=click.Path(exists=True),
    help="Path to the dataset-config.yaml file with dataset information.",
)
def publish_product(git_config, dataset_config):
    """
    Command-line interface for the ProductPublisher API.
    """
    publisher = ProductPublisher(git_config_path=git_config)
    publisher.publish_product(dataset_config_path=dataset_config)
