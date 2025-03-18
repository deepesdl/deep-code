#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.publish import Publisher


@click.command(name="publish")
@click.argument("dataset_config", type=click.Path(exists=True))
@click.argument("workflow_config", type=click.Path(exists=True))
def publish(dataset_config, workflow_config):
    """Request publishing a dataset to the open science catalogue.
    """
    publisher = Publisher(
        dataset_config_path=dataset_config, workflow_config_path=workflow_config
    )
    publisher.publish_all()
