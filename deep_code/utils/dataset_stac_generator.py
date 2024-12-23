import os
import pandas as pd
from pystac import Collection, Extent, Link, SpatialExtent, TemporalExtent
from datetime import datetime, timezone
from typing import List, Optional
from xcube.core.store import new_data_store
from deep_code.utils.osc_extension import OscExtension


class OSCProductSTACGenerator:
    """
    A class to generate OSC STAC Collections for a product from Zarr datasets.
    """

    def __init__(self, dataset_id: str):
        """
        Initialize the generator with the path to the Zarr dataset.

        :param dataset_path: Path to the Zarr dataset.
        """
        self.dataset_id = dataset_id
        self.dataset = self._open_dataset()

    def _open_dataset(self):
        """Open the dataset using a s3 store as a xarray Dataset."""
        try:
            store = new_data_store(
                "s3", root="deep-esdl-public", storage_options=dict(anon=True)
            )
            return store.open_data(self.dataset_id)
        except Exception as e:
            try:
                store = new_data_store(
                    "s3",
                    root=os.environ["S3_USER_STORAGE_BUCKET"],
                    storage_options=dict(
                        anon=False,
                        key=os.environ.get("S3_USER_STORAGE_KEY"),
                        secret=os.environ.get("S3_USER_STORAGE_SECRET"),
                    ),
                )
                return store.open_data(self.dataset_id)
            except Exception as inner_e:
                raise ValueError(
                    f"Failed to open Zarr dataset with ID "
                    f"{self.dataset_id}: {inner_e}"
                ) from e

        except Exception as e:
            raise ValueError(
                f"Failed to open Zarr dataset with ID " f"{self.dataset_id}: {e}"
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
            # Fetch 'long_name' or 'standard_name' if they exist
            long_name = variable.attrs.get("long_name")
            standard_name = variable.attrs.get("standard_name")
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
            ),
            "title": self.dataset.attrs.get("title", "No title available."),
        }

    def build_stac_collection(
        self,
        collection_id: str,
        access_link: Optional[str] = None,
        documentation_link: Optional[str] = None,
        osc_status: str = "ongoing",
        osc_region: str = "Global",
        osc_themes: Optional[List[str]] = None,
    ) -> Collection:
        """
        Build an OSC STAC Collection for the product.

        :param access_link: Public access link to the dataset.
        :param collection_id: Unique ID for the collection.
        :param documentation_link: (Optional) Link to documentation related to the dataset.
        :param osc_status: Status of the dataset (e.g., "ongoing").
        :param osc_region: Geographical region of the dataset.
        :param osc_themes: (Optional) Themes of the dataset (e.g., ["climate", "environment"]).
        :return: A pystac.Collection object.
        """

        # Set default access link if not provided, assume dataset_id is
        # already in deepesdl public s3
        if access_link is None:
            access_link = f"s3://deep-esdl-public/{self.dataset_id}"

        # Ensure osc_themes has a default value
        if osc_themes is None:
            osc_themes = []

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
            id=collection_id,
            description=general_metadata.get("description", "No description provided."),
            extent=Extent(spatial=spatial_extent, temporal=temporal_extent),
            title=general_metadata.get("title", "Unnamed Collection"),
        )

        # Add OSC extension metadata
        osc_extension = OscExtension.add_to(collection)
        # osc_project and osc_type are fixed constant values
        osc_extension.osc_project = "deep-earth-system-data-lab"
        osc_extension.osc_type = "product"
        osc_extension.osc_status = osc_status
        osc_extension.osc_region = osc_region
        osc_extension.osc_themes = osc_themes
        osc_extension.osc_variables = variables
        osc_extension.osc_missions = []

        # Add creation and update timestamps for the collection
        now_iso = datetime.now(timezone.utc).isoformat()
        collection.extra_fields["created"] = now_iso
        collection.extra_fields["updated"] = now_iso

        collection_name = f"{general_metadata.get('title', collection_id).replace(' ', '-').lower()}.json"
        collection.set_self_href(collection_name)

        collection.add_link(Link(rel="self", target=access_link, title="Access"))
        if documentation_link:
            collection.add_link(
                Link(rel="via", target=documentation_link, title="Documentation")
            )

        # Validate OSC extension fields
        try:
            osc_extension.validate_extension()
        except ValueError as e:
            raise ValueError(f"OSC Extension validation failed: {e}")

        return collection
