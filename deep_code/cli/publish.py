#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import click

from deep_code.tools.publish import Publisher, WorkflowPublisher


@click.command(name="publish-dataset")
@click.argument("dataset_config", type=click.Path(exists=True))
def publish_dataset(dataset_config):
    """Request publishing a dataset to the open science catalogue.
    """
    publisher = Publisher()
    publisher.publish_dataset(dataset_config_path=dataset_config)


@click.command(name="publish-workflow")
@click.argument("workflow_metadata", type=click.Path(exists=True))
def publish_workflow(workflow_metadata):

    workflow_publisher = WorkflowPublisher()
    workflow_publisher.publish_workflow_experiment(
        workflow_config_path=workflow_metadata
    )
