import os
import logging
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from pystac import Collection, Extent, Link, SpatialExtent, TemporalExtent
from xcube.core.store import new_data_store

from deep_code.utils.osc_extension import OscExtension


class OSCProductSTACGenerator:
    """
    A class to generate OSC STAC Collections for a product from Zarr datasets.
    """

    def __init__(
        self,
        dataset_id: str,
        collection_id: str,
        access_link: Optional[str] = None,
        documentation_link: Optional[str] = None,
        osc_status: str = "ongoing",
        osc_region: str = "Global",
        osc_themes: Optional[List[str]] = None,
        osc_missions: Optional[List[str]] = None,
    ):
        """
        Initialize the generator with the path to the Zarr dataset and metadata.

        :param dataset_id: Path to the Zarr dataset.
        :param collection_id: Unique ID for the collection.
        :param access_link: Public access link to the dataset.
        :param documentation_link: Link to documentation related to the dataset.
        :param osc_status: Status of the dataset (e.g., "ongoing").
        :param osc_region: Geographical region of the dataset.
        :param osc_themes: Themes of the dataset (e.g., ["climate", "environment"]).
        """
        self.dataset_id = dataset_id
        self.collection_id = collection_id
        self.access_link = access_link or f"s3://deep-esdl-public/{dataset_id}"
        self.documentation_link = documentation_link
        self.osc_status = osc_status
        self.osc_region = osc_region
        self.osc_themes = osc_themes or []
        self.osc_missions = osc_missions or []
        self.logger = logging.getLogger(__name__)
        self.dataset = self._open_dataset()

    def _open_dataset(self):
        """Open the dataset using a S3 store as an xarray Dataset."""

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
                    f"Attempting to open dataset with configuration: {config['description']}"
                )
                store = new_data_store(
                    config["params"]["storage_type"],
                    root=config["params"]["root"],
                    storage_options=config["params"]["storage_options"],
                )
                # Try to open the dataset; return immediately if successful
                dataset = store.open_data(self.dataset_id)
                self.logger.info(
                    f"Successfully opened dataset with configuration: {config['description']}"
                )
                return dataset
            except Exception as e:
                self.logger.error(
                    f"Failed to open dataset with configuration: {config['description']}. Error: {e}"
                )
                last_exception = e

        # If all attempts fail, raise an error
        self.logger.critical(
            f"Failed to open Zarr dataset with ID {self.dataset_id}. Tried configurations: {', '.join(tried_configurations)}. Last error: {last_exception}"
        )
        raise ValueError(
            f"Failed to open Zarr dataset with ID {self.dataset_id}. Tried configurations: {', '.join(tried_configurations)}. Last error: {last_exception}"
        )

    def _get_spatial_extent(self) -> SpatialExtent:
        """Extract spatial extent from the dataset."""
        if "lon" in self.dataset.coords and "lat" in self.dataset.coords:
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
        elif "x" in self.dataset.coords and "y" in self.dataset.coords:
            # For irregular gridding
            x_min, x_max = (float(self.dataset.x.min()), float(self.dataset.x.max()))
            y_min, y_max = (float(self.dataset.y.min()), float(self.dataset.y.max()))
            return SpatialExtent([[x_min, y_min, x_max, y_max]])
        else:
            raise ValueError(
                "Dataset does not have recognized spatial coordinates ('lon', 'lat' or 'x', 'y')."
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

    def _get_variables(self) -> List[str]:
        """
        Extract variable names from the dataset.

        Prioritize fetching `long_name` or `standard_name` from each variable's attributes.
        If neither is available, return the variable's name from `dataset.data_vars.keys()`.

        :return: A list of variable names or descriptions.
        """
        variables = []
        for var_name, variable in self.dataset.data_vars.items():
            long_name = variable.attrs.get("long_name")
            standard_name = variable.attrs.get("standard_name")
            # Replace spaces with hyphens and convert to lowercase if attributes exist
            long_name = long_name.replace(" ", "-").lower() if long_name else None
            standard_name = (
                standard_name.replace(" ", "-").lower() if standard_name else None
            )
            if not long_name and not standard_name:
                self.logger.error(
                    f"Metadata missing for variable '{var_name}': 'long_name' and 'standard_name' attributes are not available."
                )
            # Prioritize 'long_name', fallback to 'standard_name', then use variable key
            variables.append(long_name or standard_name or var_name)
        return variables

    def _get_general_metadata(self) -> dict:
        """
        Extract general metadata from the dataset attributes.
        Fallback to default values if the keys are missing.

        :return: A dictionary containing metadata such as 'description' and 'title'.
        """
        return {
            "description": self.dataset.attrs.get(
                "description", "No description available."
            )
        }

    def build_stac_collection(self) -> Collection:
        """
        Build an OSC STAC Collection for the product.

        :return: A pystac.Collection object.
        """
        # Extract metadata
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

        self_href = "https://esa-earthcode.github.io/open-science-catalog-metadata/products/deepesdl/collection.json"
        collection.set_self_href(self_href)

        # Validate OSC extension fields
        try:
            osc_extension.validate_extension()
        except ValueError as e:
            raise ValueError(f"OSC Extension validation failed: {e}")

        return collection
