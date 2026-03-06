#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
from pystac import Catalog, Item
from xarray import DataArray, Dataset

from deep_code.constants import (
    DEEPESDL_COLLECTION_SELF_HREF,
    OSC_THEME_SCHEME,
    PRODUCT_BASE_CATALOG_SELF_HREF,
    VARIABLE_BASE_CATALOG_SELF_HREF,
    ZARR_MEDIA_TYPE,
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
            workflow_id="dummy",
            workflow_title="test",
            access_link="s3://mock-bucket/mock-dataset",
            documentation_link="https://example.com/docs",
            license_type="proprietary",
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

    def test_update_product_base_catalog(self):
        """Child link is appended; existing links (including self) are untouched."""
        base = {
            "type": "Catalog",
            "id": "products",
            "stac_version": "1.0.0",
            "description": "Products",
            "links": [
                {
                    "rel": "self",
                    "href": PRODUCT_BASE_CATALOG_SELF_HREF,
                    "type": "application/json",
                }
            ],
        }
        import tempfile, json as _json

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            _json.dump(base, tmp)
            tmp_path = tmp.name

        result = self.generator.update_product_base_catalog(tmp_path)

        import os

        os.unlink(tmp_path)

        self.assertIsInstance(result, dict)
        rels = [lnk["rel"] for lnk in result["links"]]
        # self link must still be present and still first
        self.assertEqual(result["links"][0]["rel"], "self")
        self.assertEqual(result["links"][0]["href"], PRODUCT_BASE_CATALOG_SELF_HREF)
        self.assertIn("child", rels)
        child = next(lnk for lnk in result["links"] if lnk["rel"] == "child")
        self.assertIn("mock-collection-id", child["href"])

    def test_update_variable_base_catalog(self):
        """Child links for each variable are appended."""
        base = {
            "type": "Catalog",
            "id": "variables",
            "stac_version": "1.0.0",
            "description": "Variables",
            "links": [
                {
                    "rel": "self",
                    "href": VARIABLE_BASE_CATALOG_SELF_HREF,
                    "type": "application/json",
                }
            ],
        }
        import tempfile, json as _json, os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            _json.dump(base, tmp)
            tmp_path = tmp.name

        vars_ = ["v1", "v2"]
        result = self.generator.update_variable_base_catalog(tmp_path, vars_)
        os.unlink(tmp_path)

        self.assertIsInstance(result, dict)
        child_hrefs = [
            lnk["href"] for lnk in result["links"] if lnk["rel"] == "child"
        ]
        self.assertEqual(len(child_hrefs), len(vars_))
        # self link must remain in place
        self.assertEqual(result["links"][0]["rel"], "self")

    def test_update_deepesdl_collection(self):
        """Child and theme-related links are appended; existing links kept."""
        base = {
            "type": "Collection",
            "id": "deep-esdl",
            "stac_version": "1.0.0",
            "description": "DeepESDL",
            "extent": {},
            "links": [
                {
                    "rel": "self",
                    "href": DEEPESDL_COLLECTION_SELF_HREF,
                    "type": "application/json",
                }
            ],
        }
        import tempfile, json as _json, os

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            _json.dump(base, tmp)
            tmp_path = tmp.name

        result = self.generator.update_deepesdl_collection(tmp_path)
        os.unlink(tmp_path)

        self.assertIsInstance(result, dict)
        rels = [lnk["rel"] for lnk in result["links"]]
        # child link added
        self.assertIn("child", rels)
        # one related link per theme
        related = [lnk for lnk in result["links"] if lnk["rel"] == "related"]
        self.assertGreaterEqual(len(related), len(self.generator.osc_themes))
        # self link still present
        self.assertEqual(result["links"][0]["rel"], "self")

    # ------------------------------------------------------------------
    # Zarr STAC Item / Catalog generation
    # ------------------------------------------------------------------

    def test_build_zarr_stac_item_structure(self):
        """Item has correct geometry, bbox, datetime range, assets, and links."""
        s3_root = "s3://test-bucket/stac/my-collection/"
        item = self.generator.build_zarr_stac_item(s3_root)

        self.assertIsInstance(item, Item)
        self.assertEqual(item.id, "mock-collection-id")

        # Spatial
        self.assertEqual(item.bbox, [-180.0, -90.0, 180.0, 90.0])
        self.assertEqual(item.geometry["type"], "Polygon")
        coords = item.geometry["coordinates"][0]
        self.assertEqual(len(coords), 5)  # closed ring

        # Temporal — datetime must be null; start/end in properties
        self.assertIsNone(item.datetime)
        self.assertIn("start_datetime", item.properties)
        self.assertIn("end_datetime", item.properties)
        # Timezone-aware ISO strings
        self.assertTrue(item.properties["start_datetime"].endswith("+00:00"))
        self.assertTrue(item.properties["end_datetime"].endswith("+00:00"))

        # Assets
        self.assertIn("zarr-data", item.assets)
        self.assertIn("zarr-consolidated-metadata", item.assets)

        zarr_asset = item.assets["zarr-data"]
        self.assertEqual(zarr_asset.href, "s3://mock-bucket/mock-dataset")
        self.assertEqual(zarr_asset.media_type, ZARR_MEDIA_TYPE)
        self.assertIn("data", zarr_asset.roles)

        meta_asset = item.assets["zarr-consolidated-metadata"]
        self.assertEqual(
            meta_asset.href, "s3://mock-bucket/mock-dataset/.zmetadata"
        )
        self.assertIn("metadata", meta_asset.roles)

        # Self href
        self.assertEqual(
            item.self_href,
            "s3://test-bucket/stac/my-collection/mock-collection-id/item.json",
        )

        # Required link rels
        link_rels = {link.rel for link in item.links}
        self.assertIn("root", link_rels)
        self.assertIn("parent", link_rels)
        self.assertIn("collection", link_rels)

        # root and parent point to the S3 catalog
        root_link = next(lnk for lnk in item.links if lnk.rel == "root")
        self.assertEqual(
            root_link.target,
            "s3://test-bucket/stac/my-collection/catalog.json",
        )

        # collection link points to the OSC GitHub collection
        coll_link = next(lnk for lnk in item.links if lnk.rel == "collection")
        self.assertIn("open-science-catalog-metadata", coll_link.target)
        self.assertIn("mock-collection-id", coll_link.target)

    def test_build_zarr_stac_item_trailing_slash_normalised(self):
        """Trailing slash on s3_root should not produce double slashes."""
        item_with = self.generator.build_zarr_stac_item("s3://bucket/stac/")
        item_without = self.generator.build_zarr_stac_item("s3://bucket/stac")
        self.assertEqual(item_with.self_href, item_without.self_href)

    def test_build_zarr_stac_catalog_file_dict_keys(self):
        """file_dict contains exactly the catalog and item S3 paths."""
        s3_root = "s3://test-bucket/stac/my-collection/"
        file_dict = self.generator.build_zarr_stac_catalog_file_dict(s3_root)

        catalog_path = "s3://test-bucket/stac/my-collection/catalog.json"
        item_path = (
            "s3://test-bucket/stac/my-collection/mock-collection-id/item.json"
        )
        self.assertIn(catalog_path, file_dict)
        self.assertIn(item_path, file_dict)
        self.assertEqual(len(file_dict), 2)

    def test_build_zarr_stac_catalog_file_dict_content(self):
        """Catalog dict is type Catalog; item dict is type Feature with assets."""
        s3_root = "s3://test-bucket/stac/my-collection/"
        file_dict = self.generator.build_zarr_stac_catalog_file_dict(s3_root)

        catalog_dict = file_dict["s3://test-bucket/stac/my-collection/catalog.json"]
        self.assertEqual(catalog_dict["type"], "Catalog")
        self.assertEqual(catalog_dict["id"], "mock-collection-id-stac-catalog")

        item_dict = file_dict[
            "s3://test-bucket/stac/my-collection/mock-collection-id/item.json"
        ]
        self.assertEqual(item_dict["type"], "Feature")
        self.assertEqual(item_dict["id"], "mock-collection-id")
        self.assertIn("assets", item_dict)
        self.assertIn("zarr-data", item_dict["assets"])
        self.assertIn("zarr-consolidated-metadata", item_dict["assets"])

    def test_build_dataset_stac_collection_adds_s3_catalog_via_link(self):
        """A 'via' link to the S3 catalog is added when stac_catalog_s3_root is provided.

        rel='via' is used (not 'child') because the OSC validator requires every
        'child' link to resolve to a file inside the metadata repository.
        """
        s3_root = "s3://test-bucket/stac/my-collection/"
        collection = self.generator.build_dataset_stac_collection(
            mode="dataset", stac_catalog_s3_root=s3_root
        )
        s3_via = next(
            (
                lnk
                for lnk in collection.links
                if lnk.rel == "via" and "catalog.json" in str(lnk.target)
            ),
            None,
        )
        self.assertIsNotNone(s3_via, "Expected a 'via' link pointing to S3 catalog")
        self.assertEqual(
            s3_via.target,
            "s3://test-bucket/stac/my-collection/catalog.json",
        )

    def test_build_dataset_stac_collection_no_s3_via_link_by_default(self):
        """No S3 catalog 'via' link is added when stac_catalog_s3_root is absent."""
        collection = self.generator.build_dataset_stac_collection(mode="dataset")
        s3_catalog_links = [
            lnk
            for lnk in collection.links
            if lnk.rel == "via" and "catalog.json" in str(getattr(lnk, "target", ""))
        ]
        self.assertEqual(len(s3_catalog_links), 0)


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
