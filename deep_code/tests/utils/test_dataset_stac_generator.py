#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
from pystac import Catalog, Collection
from xarray import DataArray, Dataset

from deep_code.constants import (
    DEEPESDL_COLLECTION_SELF_HREF,
    OSC_THEME_SCHEME,
    PRODUCT_BASE_CATALOG_SELF_HREF,
    VARIABLE_BASE_CATALOG_SELF_HREF,
)
from deep_code.utils.dataset_stac_generator import OscDatasetStacGenerator, Theme


class TestOSCProductSTACGenerator(unittest.TestCase):
    @patch("deep_code.utils.dataset_stac_generator.open_dataset")
    def setUp(self, mock_data_store):
        """Set up a mock dataset and generator."""
        self.mock_dataset = Dataset(
            coords={
                "lon": ("lon", np.linspace(-180, 180, 10)),
                "lat": ("lat", np.linspace(-90, 90, 5)),
                "time": (
                    "time",
                    [
                        np.datetime64(datetime(2023, 1, 1), "ns"),
                        np.datetime64(datetime(2023, 1, 2), "ns"),
                    ],
                ),
            },
            attrs={"description": "Mock dataset for testing.", "title": "Mock Dataset"},
            data_vars={
                "var1": (
                    ("time", "lat", "lon"),
                    np.random.rand(2, 5, 10),
                    {
                        "description": "dummy",
                        "standard_name": "var1",
                        "gcmd_keyword_url": "https://dummy",
                    },
                ),
                "var2": (
                    ("time", "lat", "lon"),
                    np.random.rand(2, 5, 10),
                    {
                        "description": "dummy",
                        "standard_name": "var2",
                        "gcmd_keyword_url": "https://dummy",
                    },
                ),
            },
        )
        mock_store = MagicMock()
        mock_store.open_data.return_value = self.mock_dataset
        mock_data_store.return_value = self.mock_dataset

        self.generator = OscDatasetStacGenerator(
            dataset_id="mock-dataset-id",
            collection_id="mock-collection-id",
            access_link="s3://mock-bucket/mock-dataset",
            documentation_link="https://example.com/docs",
            osc_status="ongoing",
            osc_region="Global",
            osc_themes=["climate", "environment"],
        )

    def test_open_dataset(self):
        """Test if the dataset is opened correctly."""
        self.assertIsInstance(self.generator.dataset, Dataset)
        for coord in ("lon", "lat", "time"):
            self.assertIn(coord, self.generator.dataset.coords)

    def test_get_spatial_extent(self):
        """Test spatial extent extraction."""
        extent = self.generator._get_spatial_extent()
        self.assertEqual(extent.bboxes[0], [-180.0, -90.0, 180.0, 90.0])

    def test_get_temporal_extent(self):
        """Test temporal extent extraction."""
        extent = self.generator._get_temporal_extent()
        # TemporalExtent.intervals is a list of [start, end]
        interval = extent.intervals[0]
        self.assertEqual(interval[0], datetime(2023, 1, 1, 0, 0))
        self.assertEqual(interval[1], datetime(2023, 1, 2, 0, 0))

    def test_get_variables(self):
        """Test variable ID extraction."""
        vars_ = self.generator.get_variable_ids()
        self.assertCountEqual(vars_, ["var1", "var2"])

    def test_get_general_metadata(self):
        """Test general metadata extraction."""
        meta = self.generator._get_general_metadata()
        self.assertEqual(meta.get("description"), "Mock dataset for testing.")

    def test_extract_metadata_for_variable(self):
        """Test single variable metadata extraction."""
        da: DataArray = self.mock_dataset.data_vars["var1"]
        var_meta = self.generator.extract_metadata_for_variable(da)
        self.assertEqual(var_meta["variable_id"], "var1")
        self.assertEqual(var_meta["description"], "dummy")
        self.assertEqual(var_meta["gcmd_keyword_url"], "https://dummy")

    def test_get_variables_metadata(self):
        """Test metadata dict for all variables."""
        meta_dict = self.generator.get_variables_metadata()
        self.assertIn("var1", meta_dict)
        self.assertIn("var2", meta_dict)
        self.assertIsInstance(meta_dict["var1"], dict)

    def test_build_theme(self):
        """Test Theme builder static method."""
        themes = ["a", "b"]
        theme_obj: Theme = OscDatasetStacGenerator.build_theme(themes)
        self.assertEqual(theme_obj.scheme, OSC_THEME_SCHEME)
        ids = [tc.id for tc in theme_obj.concepts]
        self.assertListEqual(ids, ["a", "b"])

    @patch.object(OscDatasetStacGenerator, "_add_gcmd_link_to_var_catalog")
    @patch.object(OscDatasetStacGenerator, "add_themes_as_related_links_var_catalog")
    def test_build_variable_catalog(self, mock_add_themes, mock_add_gcmd):
        """Test building of variable-level STAC catalog."""
        var_meta = self.generator.variables_metadata["var1"]
        catalog = self.generator.build_variable_catalog(var_meta)
        self.assertIsInstance(catalog, Catalog)
        self.assertEqual(catalog.id, "var1")
        # Title should be capitalized
        self.assertEqual(catalog.title, "Var1")
        # Self href ends with var1/catalog.json
        self.assertTrue(catalog.self_href.endswith("/var1/catalog.json"))

    @patch("pystac.Catalog.from_file")
    def test_update_product_base_catalog(self, mock_from_file):
        """Test linking product catalog."""
        mock_cat = MagicMock(spec=Catalog)
        mock_from_file.return_value = mock_cat

        result = self.generator.update_product_base_catalog("path.json")
        self.assertIs(result, mock_cat)
        mock_cat.add_link.assert_called_once()
        mock_cat.set_self_href.assert_called_once_with(PRODUCT_BASE_CATALOG_SELF_HREF)

    @patch("pystac.Catalog.from_file")
    def test_update_variable_base_catalog(self, mock_from_file):
        """Test linking variable base catalog."""
        mock_cat = MagicMock(spec=Catalog)
        mock_from_file.return_value = mock_cat

        vars_ = ["v1", "v2"]
        result = self.generator.update_variable_base_catalog("vars.json", vars_)
        self.assertIs(result, mock_cat)
        # Expect one add_link per variable
        self.assertEqual(mock_cat.add_link.call_count, len(vars_))
        mock_cat.set_self_href.assert_called_once_with(VARIABLE_BASE_CATALOG_SELF_HREF)

    @patch("pystac.Collection.from_file")
    def test_update_deepesdl_collection(self, mock_from_file):
        """Test updating DeepESDL collection."""
        mock_coll = MagicMock(spec=Collection)
        mock_from_file.return_value = mock_coll

        result = self.generator.update_deepesdl_collection("deep.json")
        self.assertIs(result, mock_coll)
        # Expect child and theme related links for each theme
        calls = mock_coll.add_link.call_count
        self.assertGreaterEqual(calls, 1 + len(self.generator.osc_themes))
        mock_coll.set_self_href.assert_called_once_with(DEEPESDL_COLLECTION_SELF_HREF)


class TestFormatString(unittest.TestCase):
    def test_single_word(self):
        self.assertEqual(
            OscDatasetStacGenerator.format_string("temperature"), "Temperature"
        )
        self.assertEqual(OscDatasetStacGenerator.format_string("temp"), "Temp")
        self.assertEqual(OscDatasetStacGenerator.format_string("hello"), "Hello")

    def test_multiple_words_with_spaces(self):
        self.assertEqual(
            OscDatasetStacGenerator.format_string("surface temp"), "Surface Temp"
        )
        self.assertEqual(
            OscDatasetStacGenerator.format_string("this is a test"), "This Is A Test"
        )

    def test_multiple_words_with_underscores(self):
        self.assertEqual(
            OscDatasetStacGenerator.format_string("surface_temp"), "Surface Temp"
        )
        self.assertEqual(
            OscDatasetStacGenerator.format_string("this_is_a_test"), "This Is A Test"
        )

    def test_mixed_spaces_and_underscores(self):
        self.assertEqual(
            OscDatasetStacGenerator.format_string("surface_temp and_more"),
            "Surface Temp And More",
        )
        self.assertEqual(
            OscDatasetStacGenerator.format_string(
                "mixed_case_with_underscores_and spaces"
            ),
            "Mixed Case With Underscores And Spaces",
        )

    def test_edge_cases(self):
        # Empty string
        self.assertEqual(OscDatasetStacGenerator.format_string(""), "")
        # Single word with trailing underscore
        self.assertEqual(
            OscDatasetStacGenerator.format_string("temperature_"), "Temperature"
        )
        # Single word with leading underscore
        self.assertEqual(OscDatasetStacGenerator.format_string("_temp"), "Temp")
        # Single word with leading/trailing spaces
        self.assertEqual(OscDatasetStacGenerator.format_string("  hello  "), "Hello")
        # Multiple spaces or underscores
        self.assertEqual(
            OscDatasetStacGenerator.format_string("too___many___underscores"),
            "Too Many Underscores",
        )
        self.assertEqual(
            OscDatasetStacGenerator.format_string("too   many   spaces"),
            "Too Many Spaces",
        )
