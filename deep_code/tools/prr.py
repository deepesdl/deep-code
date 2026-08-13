#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

"""Generate a PRR-style STAC Collection -> Item -> Assets tree as local files.

The PRR (Project Results Repository) collection is a self-contained STAC tree
suitable for submission to the ESA EarthCODE PRR endpoint. It reuses the same
dataset config as the ``publish`` command but writes only local files and does
not require GitHub credentials or S3 access beyond reading the Zarr store.
"""

import logging

import fsspec
import yaml

from deep_code.utils.dataset_stac_generator import ItemConfig, OscDatasetStacGenerator

logger = logging.getLogger(__name__)


def generate_prr_collection(
    dataset_config_path: str, output_dir: str | None = None
) -> str:
    """Build and write a PRR STAC collection from a dataset config.

    Args:
        dataset_config_path: Path to the dataset config YAML (the same file used
            by ``deep-code publish``).
        output_dir: Directory to write the collection tree into. Falls back to
            ``prr_output_dir`` in the config, then ``prr/<collection_id>``.

    Returns:
        The output directory the collection tree was written to.
    """
    with fsspec.open(dataset_config_path, "r") as file:
        config = yaml.safe_load(file) or {}

    collection_id = config.get("collection_id")
    osc_project = config.get("osc_project")
    osc_project_url = config.get("osc_project_url")
    license_type = config.get("license_type")
    items_config_raw = config.get("items_config")
    if not collection_id:
        raise ValueError("collection_id is required in the dataset config.")
    if not osc_project:
        raise ValueError("osc_project is required in the dataset config.")
    if not osc_project_url:
        raise ValueError("osc_project_url is required in the dataset config.")
    if not license_type:
        raise ValueError(
            "license_type is required in the dataset config. "
            "Provide an SPDX identifier (e.g. 'CC-BY-4.0', 'MIT', 'proprietary')."
        )
    if not items_config_raw:
        raise ValueError("items_config is required in the dataset config.")
    items_config = [
        ItemConfig(
            dataset_id=item_config["dataset_id"],
            item_id=item_config["item_id"],
        )
        for item_config in items_config_raw
    ]

    logger.info(f"Generating PRR STAC collection for '{collection_id}'.")
    generator = OscDatasetStacGenerator(
        collection_id=collection_id,
        items_config=items_config,
        workflow_id=config.get("workflow_id") or "",
        workflow_title=config.get("workflow_title") or "",
        license_type=license_type,
        documentation_link=config.get("documentation_link"),
        access_link_root=config.get("access_link_root"),
        osc_status=config.get("dataset_status") or "ongoing",
        osc_region=config.get("osc_region") or "Global",
        osc_themes=config.get("osc_themes"),
        osc_missions=config.get("osc_missions"),
        cf_params=config.get("cf_parameter"),
        visualisation_link=config.get("visualisation_link"),
        description=config.get("description"),
        osc_project=config.get("osc_project"),
        osc_project_title=config.get("osc_project_title"),
        osc_project_url=config.get("osc_project_url"),
        # PRR-specific project metadata.
        osc_initiative=config.get("osc_initiative") or "earthcode",
        osc_contract_number=config.get("osc_contract_number"),
        osc_project_website=config.get("osc_project_website"),
        osc_project_description=config.get("osc_project_description"),
        thumbnail=config.get("thumbnail") or config.get("thumbnail_link"),
        thumbnail_media_type=config.get("thumbnail_media_type"),
        sci_doi=config.get("sci_doi"),
        sci_citation=config.get("sci_citation"),
    )

    out_dir = output_dir or config.get("prr_output_dir") or f"prr/{collection_id}"
    generator.save_prr_collection(out_dir)
    return out_dir
