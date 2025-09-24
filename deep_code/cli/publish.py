#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from pathlib import Path

import click

from deep_code.tools.publish import Publisher


def _validate_inputs(dataset_config, workflow_config, mode):
    mode = mode.lower()

    def ensure_file(path: str, label: str):
        if path is None:
            raise click.UsageError(f"{label} is required but was not provided.")
        if not Path(path).is_file():
            raise click.UsageError(f"{label} not found: {path}")

    if mode == "dataset":
        # Need dataset only
        ensure_file(dataset_config, "DATASET_CONFIG")
        if workflow_config is not None:
            click.echo("ℹ️ Ignoring WORKFLOW_CONFIG since mode=dataset.", err=True)

    elif mode == "workflow":
        # Need workflow config only
        ensure_file(workflow_config, "WORKFLOW_CONFIG")

    elif mode == "all":
        # Need both
        ensure_file(dataset_config, "DATASET_CONFIG")
        ensure_file(workflow_config, "WORKFLOW_CONFIG")

    else:
        raise click.UsageError(
            "Invalid mode. Choose one of: all, dataset, workflow_experiment."
        )


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
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["all", "dataset", "workflow"], case_sensitive=False),
    default="all",
    help="Publishing mode: dataset only, workflow only, or both",
)
def publish(dataset_config, workflow_config, environment, mode):
    """Request publishing a dataset along with experiment and workflow metadata to the
    open science catalogue.
    """
    publisher = Publisher(
        dataset_config_path=dataset_config,
        workflow_config_path=workflow_config,
        environment=environment.lower(),
    )
    result = publisher.publish(mode=mode.lower())
    click.echo(f"Pull request created: {result}")
