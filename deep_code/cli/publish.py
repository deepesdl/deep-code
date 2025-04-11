#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.publish import Publisher


@click.command(name="publish")
@click.argument("dataset_config", type=click.Path(exists=True))
@click.argument("workflow_config", type=click.Path(exists=True))
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["production", "staging", "testing"], case_sensitive=False),
    default="production",
    help="Target environment for publishing (production, staging, testing)",
)
def publish(dataset_config, workflow_config, environment):
    """Request publishing a dataset along with experiment and workflow metadata to the
    open science catalogue.
    """
    publisher = Publisher(
        dataset_config_path=dataset_config,
        workflow_config_path=workflow_config,
        environment=environment.lower(),
    )
    publisher.publish_all()
