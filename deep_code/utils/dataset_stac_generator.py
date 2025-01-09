#!/usr/bin/env python3

# Copyright (c) 2024 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import os
import logging
from datetime import datetime, timezone

import pandas as pd
from pystac import Collection, Extent, Link, SpatialExtent, TemporalExtent
from xcube.core.store import new_data_store

from deep_code.utils.osc_extension import OscExtension


class OSCProductSTACGenerator:
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

        self.logger.critical(
            f"Failed to open Zarr dataset with ID {self.dataset_id}. "
            f"Tried configurations: {', '.join(tried_configurations)}. "
            f"Last error: {last_exception}"
        )
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

    def _get_variables(self) -> list[str]:
        """Extracts variable names or descriptions from the dataset.

        Variables are prioritized based on their `long_name` or `standard_name`
        attributes. If neither is available, the variable's key from
        `dataset.data_vars.keys()` is used.

        Returns:
            A list of variable names or descriptions.
        """
        variables = []
        for var_name, variable in self.dataset.data_vars.items():
            long_name = self._normalize_name(variable.attrs.get("long_name"))
            standard_name = self._normalize_name(variable.attrs.get("standard_name"))
            if not long_name and not standard_name:
                self.logger.error(
                    f"Metadata missing for variable '{var_name}': 'long_name' and "
                    f"'standard_name' attributes are not available."
                )
            # Prioritize 'long_name', fallback to 'standard_name', then use variable key
            variables.append(long_name or standard_name or var_name)
        return variables

    def _get_general_metadata(self) -> dict:
        return {
            "description": self.dataset.attrs.get(
                "description", "No description available."
            )
        }

    def build_stac_collection(self) -> Collection:
        """
        Build an OSC STAC Collection for the dataset.

        :return: A pystac.Collection object.
        """
        try:
            spatial_extent = self._get_spatial_extent()
            temporal_extent = self._get_temporal_extent()
            variables = self._get_variables()
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
            osc_extension.cf_parameter = [{"Name": self.collection_id}]

        # Add creation and update timestamps for the collection
        now_iso = datetime.now(timezone.utc).isoformat()
        collection.extra_fields["created"] = now_iso
        collection.extra_fields["updated"] = now_iso

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
