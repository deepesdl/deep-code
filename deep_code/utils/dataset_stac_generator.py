#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import os
import logging
from datetime import datetime, timezone

import pandas as pd
import requests
from pystac import Collection, Extent, Link, SpatialExtent, TemporalExtent, Catalog
from urllib.parse import quote_plus
from xcube.core.store import new_data_store

from deep_code.utils.osc_extension import OscExtension


class OSCDatasetSTACGenerator:
    """Generates OSC STAC Collections for a product from Zarr datasets.

    Args:
        dataset_id: ID of the Zarr dataset.
        collection_id: Unique identifier for the STAC collection.
        access_link: Public access link to the dataset.
        documentation_link: Link to dataset documentation.
        osc_status: Status of the dataset (e.g., "ongoing").
        osc_region: Geographical region associated with the dataset.
        osc_themes: List of themes related to the dataset (e.g., ["climate"]).
        osc_missions: List of satellite missions associated with the dataset.
        cf_params: CF metadata parameters for the dataset.
    """

    def __init__(
        self,
        dataset_id: str,
        collection_id: str,
        access_link: str | None = None,
        documentation_link: str | None = None,
        osc_status: str = "ongoing",
        osc_region: str = "Global",
        osc_themes: list[str] | None = None,
        osc_missions: list[str] | None = None,
        cf_params: list[dict[str]] | None = None,
    ):
        self.dataset_id = dataset_id
        self.collection_id = collection_id
        self.access_link = access_link or f"s3://deep-esdl-public/{dataset_id}"
        self.documentation_link = documentation_link
        self.osc_status = osc_status
        self.osc_region = osc_region
        self.osc_themes = osc_themes or []
        self.osc_missions = osc_missions or []
        self.cf_params = cf_params or {}
        self.logger = logging.getLogger(__name__)
        self.dataset = self._open_dataset()
        self.variables_metadata = self.get_variables_metadata()

    def _open_dataset(self):
        """Open the dataset using a S3 store as a xarray Dataset."""

        store_configs = [
            {
                "description": "Public store",
                "params": {
                    "storage_type": "s3",
                    "root": "deep-esdl-public",
                    "storage_options": {"anon": True},
                },
            },
            {
                "description": "Authenticated store",
                "params": {
                    "storage_type": "s3",
                    "root": os.environ.get("S3_USER_STORAGE_BUCKET"),
                    "storage_options": {
                        "anon": False,
                        "key": os.environ.get("S3_USER_STORAGE_KEY"),
                        "secret": os.environ.get("S3_USER_STORAGE_SECRET"),
                    },
                },
            },
        ]

        # Iterate through configurations and attempt to open the dataset
        last_exception = None
        tried_configurations = []
        for config in store_configs:
            tried_configurations.append(config["description"])
            try:
                self.logger.info(
                    f"Attempting to open dataset with configuration: "
                    f"{config['description']}"
                )
                store = new_data_store(
                    config["params"]["storage_type"],
                    root=config["params"]["root"],
                    storage_options=config["params"]["storage_options"],
                )
                dataset = store.open_data(self.dataset_id)
                self.logger.info(
                    f"Successfully opened dataset with configuration: "
                    f"{config['description']}"
                )
                return dataset
            except Exception as e:
                self.logger.error(
                    f"Failed to open dataset with configuration: "
                    f"{config['description']}. Error: {e}"
                )
                last_exception = e

        raise ValueError(
            f"Failed to open Zarr dataset with ID {self.dataset_id}. "
            f"Tried configurations: {', '.join(tried_configurations)}. "
            f"Last error: {last_exception}"
        )

    def _get_spatial_extent(self) -> SpatialExtent:
        """Extract spatial extent from the dataset."""
        if {"lon", "lat"}.issubset(self.dataset.coords):
            # For regular gridding
            lon_min, lon_max = (
                float(self.dataset.lon.min()),
                float(self.dataset.lon.max()),
            )
            lat_min, lat_max = (
                float(self.dataset.lat.min()),
                float(self.dataset.lat.max()),
            )
            return SpatialExtent([[lon_min, lat_min, lon_max, lat_max]])
        elif {"longitude", "latitude"}.issubset(self.dataset.coords):
            # For regular gridding with 'longitude' and 'latitude'
            lon_min, lon_max = (
                float(self.dataset.longitude.min()),
                float(self.dataset.longitude.max()),
            )
            lat_min, lat_max = (
                float(self.dataset.latitude.min()),
                float(self.dataset.latitude.max()),
            )
            return SpatialExtent([[lon_min, lat_min, lon_max, lat_max]])
        elif {"x", "y"}.issubset(self.dataset.coords):
            # For irregular gridding
            x_min, x_max = (float(self.dataset.x.min()), float(self.dataset.x.max()))
            y_min, y_max = (float(self.dataset.y.min()), float(self.dataset.y.max()))
            return SpatialExtent([[x_min, y_min, x_max, y_max]])
        else:
            raise ValueError(
                "Dataset does not have recognized spatial coordinates "
                "('lon', 'lat' or 'x', 'y')."
            )

    def _get_temporal_extent(self) -> TemporalExtent:
        """Extract temporal extent from the dataset."""
        if "time" in self.dataset.coords:
            try:
                # Convert the time bounds to datetime objects
                time_min = pd.to_datetime(
                    self.dataset.time.min().values
                ).to_pydatetime()
                time_max = pd.to_datetime(
                    self.dataset.time.max().values
                ).to_pydatetime()
                return TemporalExtent([[time_min, time_max]])
            except Exception as e:
                raise ValueError(f"Failed to parse temporal extent: {e}")
        else:
            raise ValueError("Dataset does not have a 'time' coordinate.")

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        return name.replace(" ", "-").lower() if name else None

    def _get_general_metadata(self) -> dict:
        return {
            "description": self.dataset.attrs.get(
                "description", "No description available."
            )
        }

    def extract_metadata_for_variable(self, variable_data) -> dict:
        """Extract metadata for a single variable."""
        long_name = variable_data.attrs.get("long_name")
        standard_name = variable_data.attrs.get("standard_name")
        title = long_name or standard_name or variable_data.name
        description = variable_data.attrs.get("description", "No variable description")
        gcmd_keyword_url = variable_data.attrs.get("gcmd_keyword_url")
        return {
            "variable_id": self._normalize_name(title),
            "description": description,
            "gcmd_keyword_url": gcmd_keyword_url,
        }

    def get_variable_ids(self) -> list[str]:
        """Get variable IDs for all variables in the dataset."""
        return list(self.variables_metadata.keys())

    def get_variables_metadata(self) -> dict[str, dict]:
        """Extract metadata for all variables in the dataset."""
        variables_metadata = {}
        for var_name, variable in self.dataset.data_vars.items():
            var_metadata = self.extract_metadata_for_variable(variable)
            variables_metadata[var_metadata.get("variable_id")] = var_metadata
        return variables_metadata

    def _add_gcmd_link_to_var_catalog(
        self, var_catalog: Catalog, var_metadata: dict
    ) -> None:
        """
        Checks for a GCMD keyword URL in var_metadata, adds a 'via' link to the catalog
        pointing to the GCMD Keyword Viewer.

        Args:
            var_catalog: The PySTAC Catalog to which we want to add the link.
            var_metadata: Dictionary containing metadata about the variable,
                          including 'gcmd_keyword_url'.
        """
        gcmd_keyword_url = var_metadata.get("gcmd_keyword_url")
        if not gcmd_keyword_url:
            self.logger.debug(
                f"No gcmd_keyword_url in var_metadata. Skipping adding GCMD link in "
                f'the {var_metadata.get("variable_id")} catalog'
            )
            return
        var_catalog.add_link(
            Link(
                rel="via",
                target=gcmd_keyword_url,
                title="Description",
                media_type="text/html",
            )
        )
        self.logger.info(
            f'Added GCMD link for {var_metadata.get("variable_id")} '
            f"catalog {gcmd_keyword_url}."
        )

    def build_variable_catalog(self, var_metadata) -> Catalog:
        """Build an OSC STAC Catalog for the variables in the dataset.

        Returns:
            A pystac.Catalog object.
        """
        var_id = var_metadata.get("variable_id")
        concepts = [{"id": theme} for theme in self.osc_themes]

        themes = [
            {
                "scheme": "https://github.com/stac-extensions/osc#theme",
                "concepts": concepts,
            }
        ]

        now_iso = datetime.now(timezone.utc).isoformat()

        # Create a PySTAC Catalog object
        var_catalog = Catalog(
            id=var_id,
            description=var_metadata.get("description"),
            title=var_id,
            stac_extensions=[
                "https://stac-extensions.github.io/themes/v1.0.0/schema.json"
            ],
        )

        var_catalog.stac_version = "1.0.0"
        var_catalog.extra_fields["updated"] = now_iso
        var_catalog.keywords = []

        # Add the 'themes' block (from your example JSON)
        var_catalog.extra_fields["themes"] = themes

        var_catalog.remove_links("root")
        # Add relevant links
        var_catalog.add_link(
            Link(
                rel="root",
                target="../../catalog.json",
                media_type="application/json",
                title="Open Science Catalog",
            )
        )

        # 'child' link: points to the product (or one of its collections) using this variable
        var_catalog.add_link(
            Link(
                rel="child",
                target=f"../../products/{self.collection_id}/collection.json",
                media_type="application/json",
                title=self.collection_id,
            )
        )

        # 'parent' link: back up to the variables overview
        var_catalog.add_link(
            Link(
                rel="parent",
                target="../catalog.json",
                media_type="application/json",
                title="Variables",
            )
        )
        # Add gcmd link for the variable definition
        self._add_gcmd_link_to_var_catalog(var_catalog, var_metadata)

        self_href = (
            f"https://esa-earthcode.github.io/open-science-catalog-metadata/variables"
            f"/{var_id}/catalog.json"
        )
        # 'self' link: the direct URL where this JSON is hosted
        var_catalog.set_self_href(self_href)

        return var_catalog

    def update_existing_variable_catalog(self, var_file_path, var_id) -> Catalog:
        existing_catalog = Catalog.from_file(var_file_path)
        now_iso = datetime.now(timezone.utc).isoformat()
        existing_catalog.extra_fields["updated"] = now_iso

        # add 'child' link as the product
        existing_catalog.add_link(
            Link(
                rel="child",
                target=f"../../products/{self.collection_id}/collection.json",
                media_type="application/json",
                title=self.collection_id,
            )
        )
        self_href = (
            f"https://esa-earthcode.github.io/open-science-catalog-metadata/variables"
            f"/{var_id}/catalog.json"
        )
        # 'self' link: the direct URL where this JSON is hosted
        existing_catalog.set_self_href(self_href)

        return existing_catalog

    def build_dataset_stac_collection(self) -> Collection:
        """Build an OSC STAC Collection for the dataset.

        Returns:
            A pystac.Collection object.
        """
        try:
            spatial_extent = self._get_spatial_extent()
            temporal_extent = self._get_temporal_extent()
            variables = self.get_variable_ids()
            general_metadata = self._get_general_metadata()
        except ValueError as e:
            raise ValueError(f"Metadata extraction failed: {e}")

        # Build base STAC Collection
        collection = Collection(
            id=self.collection_id,
            description=general_metadata.get("description", "No description provided."),
            extent=Extent(spatial=spatial_extent, temporal=temporal_extent),
        )

        # Add OSC extension metadata
        osc_extension = OscExtension.add_to(collection)
        # osc_project and osc_type are fixed constant values
        osc_extension.osc_project = "deep-earth-system-data-lab"
        osc_extension.osc_type = "product"
        osc_extension.osc_status = self.osc_status
        osc_extension.osc_region = self.osc_region
        osc_extension.osc_themes = self.osc_themes
        osc_extension.osc_variables = variables
        osc_extension.osc_missions = self.osc_missions
        if self.cf_params:
            osc_extension.cf_parameter = self.cf_params
        else:
            osc_extension.cf_parameter = [{"name": self.collection_id}]

        # Add creation and update timestamps for the collection
        now_iso = datetime.now(timezone.utc).isoformat()
        collection.extra_fields["created"] = now_iso
        collection.extra_fields["updated"] = now_iso
        collection.title = self.collection_id

        # Remove any existing root link and re-add it properly
        collection.remove_links("root")
        collection.add_link(
            Link(
                rel="root",
                target="../../catalog.json",
                media_type="application/json",
                title="Open Science Catalog",
            )
        )
        collection.add_link(Link(rel="via", target=self.access_link, title="Access"))
        if self.documentation_link:
            collection.add_link(
                Link(rel="via", target=self.documentation_link, title="Documentation")
            )
        collection.add_link(
            Link(
                rel="parent",
                target="../catalog.json",
                media_type="application/json",
                title="Products",
            )
        )
        # Add variables ref
        for var in variables:
            collection.add_link(
                Link(
                    rel="related",
                    target=f"../../varibales/{var}/catalog.json",
                    media_type="application/json",
                    title="Variable: " + var,
                )
            )

        self_href = (
            "https://esa-earthcode.github.io/"
            "open-science-catalog-metadata/products/deepesdl/collection.json"
        )
        collection.set_self_href(self_href)

        # Validate OSC extension fields
        try:
            osc_extension.validate_extension()
        except ValueError as e:
            raise ValueError(f"OSC Extension validation failed: {e}")

        return collection
