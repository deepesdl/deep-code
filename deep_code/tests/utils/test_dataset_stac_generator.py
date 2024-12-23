import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from deep_code.utils.dataset_stac_generator import OSCProductSTACGenerator
from pystac import Collection
from xarray import Dataset
import numpy as np


class TestOSCProductSTACGenerator(unittest.TestCase):

    @patch("deep_code.utils.dataset_stac_generator.new_data_store")
    def setUp(self, mock_data_store):
        """Set up a mock dataset and generator."""
        self.mock_dataset = Dataset(
            coords={
                "lon": ("lon", np.linspace(-180, 180, 10)),
                "lat": ("lat", np.linspace(-90, 90, 5)),
                "time": (
                    "time",
                    [np.datetime64("2023-01-01T00:00:00Z", "ns"), np.datetime64("2023-01-02T00:00:00Z", "ns")]
                ),
            },
            attrs={
                "description": "Mock dataset for testing.",
                "title": "Mock Dataset",
            },
            data_vars={
                "var1": (("time", "lat", "lon"), np.random.rand(2, 5, 10)),
                "var2": (("time", "lat", "lon"), np.random.rand(2, 5, 10)),
            }
        )
        mock_store = MagicMock()
        mock_store.open_data.return_value = self.mock_dataset
        mock_data_store.return_value = mock_store

        self.generator = OSCProductSTACGenerator("mock-dataset-id")

    def test_open_dataset(self):
        """Test if the dataset is opened correctly."""
        self.assertIsInstance(self.generator.dataset, Dataset)
        self.assertIn("lon", self.generator.dataset.coords)
        self.assertIn("lat", self.generator.dataset.coords)
        self.assertIn("time", self.generator.dataset.coords)

    def test_get_spatial_extent(self):
        """Test spatial extent extraction."""
        extent = self.generator._get_spatial_extent()
        self.assertEqual(extent.bboxes[0], [-180.0, -90.0, 180.0, 90.0])

    def test_get_temporal_extent(self):
        """Test temporal extent extraction."""
        extent = self.generator._get_temporal_extent()
        expected_intervals = [
            datetime(2023, 1, 1, 0, 0),
            datetime(2023, 1, 2, 0, 0),
        ]
        self.assertEqual(extent.intervals[0], expected_intervals)

    def test_get_variables(self):
        """Test variable extraction."""
        variables = self.generator._get_variables()
        self.assertEqual(variables, ["var1", "var2"])

    def test_get_general_metadata(self):
        """Test general metadata extraction."""
        metadata = self.generator._get_general_metadata()
        self.assertEqual(metadata["description"], "Mock dataset for testing.")
        self.assertEqual(metadata["title"], "Mock Dataset")

    @patch("pystac.Collection.add_link")
    @patch("pystac.Collection.set_self_href")
    def test_build_stac_collection(self, mock_set_self_href, mock_add_link):
        """Test STAC collection creation."""
        collection = self.generator.build_stac_collection(
            collection_id="mock-collection-id",
            access_link="s3://mock-bucket/mock-dataset",
            documentation_link="https://example.com/docs",
            osc_status="ongoing",
            osc_region="Global",
            osc_themes=["climate", "environment"],
        )
        self.assertIsInstance(collection, Collection)
        self.assertEqual(collection.id, "mock-collection-id")
        self.assertEqual(collection.description, "Mock dataset for testing.")
        self.assertEqual(collection.title, "Mock Dataset")
        self.assertEqual(collection.extent.spatial.bboxes[0], [-180.0, -90.0, 180.0, 90.0])
        self.assertEqual(
            collection.extent.temporal.intervals[0],
            [datetime(2023, 1, 1, 0, 0), datetime(2023, 1, 2, 0, 0)],
        )
        mock_set_self_href.assert_called_once()
        mock_add_link.assert_called()

    def test_invalid_spatial_extent(self):
        """Test spatial extent extraction with missing coordinates."""
        self.generator.dataset = Dataset(coords={"x": [], "y": []})
        with self.assertRaises(ValueError):
            self.generator._get_spatial_extent()

    def test_invalid_temporal_extent(self):
        """Test temporal extent extraction with missing time."""
        self.generator.dataset = Dataset(coords={})
        with self.assertRaises(ValueError):
            self.generator._get_temporal_extent()

