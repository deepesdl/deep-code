import os

import xarray as xr
from pystac import Collection, Extent, SpatialExtent, TemporalExtent
from pystac.extensions.base import PropertiesExtension
from datetime import datetime
from typing import List
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
        """Open the Zarr dataset as an xarray Dataset."""
        try:
            store = new_data_store('s3', root=os.environ["S3_USER_STORAGE_BUCKET"],
                                   storage_options=dict(anon=False,
                                                        key=os.environ["S3_USER_STORAGE_KEY"],
                                                        secret=os.environ[
                                                        "S3_USER_STORAGE_SECRET"]))
            return store.open_data(self.dataset_id)
        except Exception as e:
            raise ValueError(f"Failed to open Zarr dataset at "
                             f"{self.dataset_id}: {e}")

    def _get_spatial_extent(self) -> SpatialExtent:
        """Extract spatial extent from the dataset."""
        if "longitude" in self.dataset.coords and "latitude" in self.dataset.coords:
            lon_min, lon_max = (
                float(self.dataset.longitude.min()),
                float(self.dataset.longitude.max()),
            )
            lat_min, lat_max = (
                float(self.dataset.latitude.min()),
                float(self.dataset.latitude.max()),
            )
            return SpatialExtent([[lon_min, lat_min, lon_max, lat_max]])
        else:
            raise ValueError(
                "Dataset does not have 'longitude' and 'latitude' coordinates."
            )

    def _get_temporal_extent(self) -> TemporalExtent:
        """Extract temporal extent from the dataset."""
        if "time" in self.dataset.coords:
            time_min = str(self.dataset.time.min().values)
            time_max = str(self.dataset.time.max().values)
            return TemporalExtent([[time_min, time_max]])
        else:
            raise ValueError("Dataset does not have a 'time' coordinate.")

    def _get_variables(self) -> List[str]:
        """Extract the variable names from the dataset."""
        return list(self.dataset.data_vars.keys())

    def _get_general_metadata(self) -> dict:
        return {'description': self.dataset.attrs['description'],
                'title': self.dataset.attrs['title']}

    def build_stac_collection(
        self,
        collection_id: str,
        osc_status: str = "ongoing",
        osc_region: str = "Global",
        osc_themes: List[str] = None,
    ) -> Collection:
        """
        Build an OSC STAC Collection for the product.

        :param collection_id: Unique ID for the collection.
        :param description: Description of the collection.
        :param title: Title of the collection.
        :param osc_project: Project name for OSC metadata.
        :param osc_status: Status of the dataset (e.g., "ongoing").
        :param osc_region: Geographical region of the dataset.
        :param osc_themes: Themes of the dataset (e.g., ["climate", "environment"]).
        :return: A pystac.Collection object.
        """
        # if osc_themes is None:
        #     osc_themes = []

        # Extract metadata
        spatial_extent = self._get_spatial_extent()
        temporal_extent = self._get_temporal_extent()
        variables = self._get_variables()
        description, title = self._get_general_metadata()

        # Build base STAC Collection
        collection = Collection(
            id=collection_id,
            description=description,
            extent=Extent(spatial=spatial_extent, temporal=temporal_extent),
            title=title,
        )

        # Add OSC extension metadata
        osc_extension = OscExtension.add_to(collection)
        osc_extension.osc_project = "deep-earth-system-data-lab"
        osc_extension.osc_type = "product"
        osc_extension.osc_status = osc_status
        osc_extension.osc_region = osc_region
        osc_extension.osc_themes = osc_themes
        osc_extension.osc_variables = variables
        osc_extension.osc_missions = []
        collection.extra_fields["created"] = datetime.utcnow().isoformat() + "Z"
        collection.extra_fields["updated"] = datetime.utcnow().isoformat() + "Z"

        return collection


# Example Usage
if __name__ == "__main__":
    zarr_dataset_path = "path/to/zarr/dataset"
    collection_id = "example-collection-id"
    description = "An example OSC collection built from a Zarr dataset."
    title = "Example Collection"

    try:
        generator = OSCProductSTACGenerator(zarr_dataset_path)
        collection = generator.build_stac_collection(
            collection_id=collection_id
        )
        print(collection.to_dict())
    except Exception as e:
        print(f"Error: {e}")
