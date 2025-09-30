#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from pathlib import Path
from typing import Literal

import click
import yaml

from deep_code.tools.publish import Publisher

Mode = Literal["all", "dataset", "workflow"]

DATASET_MARKERS = {
    "stac_version",
    "extent",
    "license",
    "summaries",
    "assets",
    "providers",
    "collection",
    "collection_id",
    "id",
}
WORKFLOW_MARKERS = {
    "workflow",
    "workflow_id",
    "workflow_title",
    "experiment",
    "jupyter_notebook_url",
    "notebook",
    "parameters",
    "input_datasets",
}


def _validate_inputs(
    dataset_config: str | None, workflow_config: str | None, mode: str
):
    mode = mode.lower()

    def ensure_file(path: str | None, label: str):
        if path is None:
            raise click.UsageError(f"{label} is required but was not provided.")
        if not Path(path).is_file():
            raise click.UsageError(f"{label} not found: {path} is not a file")

    if mode == "dataset":
        ensure_file(dataset_config, "DATASET_CONFIG")
        if workflow_config is not None:
            click.echo("Ignoring WORKFLOW_CONFIG since mode=dataset.", err=True)

    elif mode == "workflow":
        ensure_file(workflow_config, "WORKFLOW_CONFIG")

    elif mode == "all":
        ensure_file(dataset_config, "DATASET_CONFIG")
        ensure_file(workflow_config, "WORKFLOW_CONFIG")

    else:
        raise click.UsageError("Invalid mode. Choose one of: all, dataset, workflow.")


def _detect_config_type(path: Path) -> Literal["dataset", "workflow"]:
    """Detect config type via filename hints and YAML top-level keys."""
    name = path.name.lower()
    if "workflow" in name or "experiment" in name:
        return "workflow"
    if "dataset" in name or "collection" in name:
        return "dataset"

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Cannot read YAML from {path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"YAML in {path} must be a mapping/object at the top level.")

    keys = set(data.keys())
    ds_score = len(keys & DATASET_MARKERS)
    wf_score = len(keys & WORKFLOW_MARKERS)

    if ds_score > wf_score:
        return "dataset"
    if wf_score > ds_score:
        return "workflow"

    raise ValueError(
        f"Ambiguous config type for {path}. "
        "Rename to include 'dataset' or 'workflow', or pass the missing file explicitly."
    )


def _assign_configs(
    pos_first: str | None,
    pos_second: str | None,
    mode: Mode,
    explicit_dataset: str | None,
    explicit_workflow: str | None,
) -> tuple[str | None, str | None]:
    """
    Decide which file is dataset vs workflow.
    Precedence: explicit flags > positional + detection.
    Returns (dataset_config, workflow_config).
    """
    ds = explicit_dataset
    wf = explicit_workflow

    # If both explicit provided, we're done; warn if extra positionals are passed.
    pos_args = [p for p in (pos_first, pos_second) if p]
    if ds and wf:
        if pos_args:
            click.echo(
                "Positional config paths ignored because explicit flags were provided.",
                err=True,
            )
        return ds, wf

    # Helper to assign a single positional file to the missing slot
    def _assign_single(p: str) -> tuple[str | None, str | None]:
        nonlocal ds, wf
        if ds and wf:
            raise click.UsageError(
                "Both dataset and workflow configs already provided; remove extra positional files."
            )
        # Use mode as a strong hint when only one is missing
        if not ds and mode == "dataset":
            ds = p
            return
        if not wf and mode == "workflow":
            wf = p
            return
        # Otherwise detect
        kind = _detect_config_type(Path(p))
        if kind == "dataset":
            if ds and Path(ds).resolve() != Path(p).resolve():
                raise click.UsageError(
                    f"Multiple dataset configs supplied: {ds} and {p}"
                )
            ds = p
        else:
            if wf and Path(wf).resolve() != Path(p).resolve():
                raise click.UsageError(
                    f"Multiple workflow configs supplied: {wf} and {p}"
                )
            wf = p

    # If exactly one explicit provided, try to fill the other via positionals
    if ds and not wf:
        if len(pos_args) > 1:
            raise click.UsageError(
                "Provide at most one positional file when using --dataset-config."
            )
        if pos_args:
            _assign_single(pos_args[0])
        return ds, wf

    if wf and not ds:
        if len(pos_args) > 1:
            raise click.UsageError(
                "Provide at most one positional file when using --workflow-config."
            )
        if pos_args:
            _assign_single(pos_args[0])
        return ds, wf

    # No explicit flags: rely on positionals + detection
    if not pos_args:
        return None, None
    if len(pos_args) == 1:
        p = pos_args[0]
        if mode == "dataset":
            return p, None
        if mode == "workflow":
            return None, p
        # mode == "all": detect and require the other later in validation
        kind = _detect_config_type(Path(p))
        return (p, None) if kind == "dataset" else (None, p)

    # Two positionals: detect both and assign
    p1, p2 = pos_args[0], pos_args[1]
    k1 = _detect_config_type(Path(p1))
    k2 = _detect_config_type(Path(p2))
    if k1 == k2:
        raise click.UsageError(
            f"Both files look like '{k1}' configs: {p1} and {p2}. "
            "Please rename one or use --dataset-config/--workflow-config."
        )
    ds = p1 if k1 == "dataset" else p2
    wf = p1 if k1 == "workflow" else p2
    return ds, wf


@click.command(name="publish")
@click.argument("dataset_config", type=click.Path(exists=True), required=False)
@click.argument("workflow_config", type=click.Path(exists=True), required=False)
@click.option(
    "--dataset-config",
    "dataset_config_opt",
    type=click.Path(exists=True),
    help="Explicit path to dataset config (overrides positional detection).",
)
@click.option(
    "--workflow-config",
    "workflow_config_opt",
    type=click.Path(exists=True),
    help="Explicit path to workflow config (overrides positional detection).",
)
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
def publish(
    dataset_config,
    workflow_config,
    dataset_config_opt,
    workflow_config_opt,
    environment,
    mode,
):
    """
    Publish dataset and/or workflow/experiment metadata.

    Examples:
      deep-code publish workflow.yaml -e staging -m workflow
      deep-code publish dataset.yaml -e staging -m dataset
      deep-code publish dataset.yaml workflow.yaml -m all
      deep-code publish --dataset-config dataset.yaml --workflow-config wf.yaml -m all
      deep-code publish --dataset-config dataset.yaml -m dataset
      deep-code publish --workflow-config wf.yaml -m workflow
    """
    mode = mode.lower()
    ds_path, wf_path = _assign_configs(
        dataset_config,
        workflow_config,
        mode,  # type: ignore[arg-type]
        dataset_config_opt,
        workflow_config_opt,
    )

    _validate_inputs(ds_path, wf_path, mode)

    publisher = Publisher(
        dataset_config_path=ds_path,
        workflow_config_path=wf_path,
        environment=environment.lower(),
    )
    result = publisher.publish(mode=mode)

    click.echo(result if isinstance(result, str) else "Wrote files locally.")
