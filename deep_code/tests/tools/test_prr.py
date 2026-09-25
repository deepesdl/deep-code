#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import numpy as np
import yaml
from xarray import Dataset

from deep_code.tools.prr import generate_prr_collection


def _make_dataset():
    return Dataset(
        coords={
            "lon": ("lon", np.linspace(-20, 20, 4)),
            "lat": ("lat", np.linspace(-10, 10, 3)),
            "time": ("time", [np.datetime64(datetime(2021, 1, 1), "ns")]),
        },
        data_vars={
            "sst": (
                ("time", "lat", "lon"),
                np.random.rand(1, 3, 4),
                {"units": "K", "long_name": "Sea surface temperature"},
            )
        },
        attrs={
            "description": "PRR tool test cube",
            # set by open_dataset from the store's file sizes
            "size": 123456,
            "metadata_size": 123,
        },
    )


class TestGeneratePrrCollection(unittest.TestCase):
    def _write_config(self, tmp, **overrides):
        config = {
            "collection_id": "tool-prr",
            "items_config": [{"dataset_id": "test.zarr", "item_id": "tool-item"}],
            "license_type": "CC-BY-4.0",
            "osc_project": "tool-project",
            "osc_project_url": "https://project.example.org",
            "osc_status": "ongoing",
            "osc_region": "Global",
            "osc_themes": ["oceans"],
            "documentation_link": "https://example.org",
        }
        config.update(overrides)
        path = os.path.join(tmp, "dataset-config.yaml")
        with open(path, "w") as f:
            yaml.safe_dump(config, f)
        return path

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda *args, **kwargs: _make_dataset(),
    )
    def test_writes_collection_tree(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            out = os.path.join(tmp, "out")
            result = generate_prr_collection(config_path, output_dir=out)

            self.assertEqual(result, out)
            coll_path = os.path.join(out, "tool-prr", "collection.json")
            item_path = os.path.join(out, "tool-prr", "items", "tool-item.json")
            self.assertTrue(os.path.isfile(coll_path))
            self.assertTrue(os.path.isfile(item_path))
            with open(coll_path) as f:
                coll = json.load(f)
            self.assertEqual(coll["id"], "tool-prr")
            self.assertEqual(coll["type"], "Collection")
            self.assertEqual(coll["osc:type"], "product")
            self.assertEqual(coll["osc:status"], "ongoing")
            with open(item_path) as f:
                item = json.load(f)
            # PRR ingests the Zarr next to the item, so asset hrefs are relative.
            self.assertEqual(item["assets"]["zarr-data"]["href"], "./test.zarr")

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda *args, **kwargs: _make_dataset(),
    )
    def test_default_output_dir_from_collection_id(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                out = generate_prr_collection(config_path)
                self.assertEqual(out, "prr")
                self.assertTrue(
                    os.path.isfile(os.path.join(out, "tool-prr", "collection.json"))
                )
            finally:
                os.chdir(cwd)

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda *args, **kwargs: _make_dataset(),
    )
    def test_output_dir_from_config(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "from-config")
            config_path = self._write_config(tmp, prr_output_dir=out)
            result = generate_prr_collection(config_path)
            self.assertEqual(result, out)
            self.assertTrue(
                os.path.isfile(os.path.join(out, "tool-prr", "collection.json"))
            )

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda *args, **kwargs: _make_dataset(),
    )
    def test_prr_spec_fields_plumbed_from_config(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            config_path = self._write_config(
                tmp,
                osc_missions=["sentinel-3"],
                osc_project_description="Project description.",
                osc_project_website="https://project.example.org",
                osc_contract_number="4000114410/15/NL/BW",
                thumbnail="https://example.org/logo.jpeg",
                sci_doi="10.1000/xyz123",
            )
            generate_prr_collection(config_path, output_dir=out)
            with open(os.path.join(out, "tool-prr", "collection.json")) as f:
                coll = json.load(f)
            self.assertEqual(coll["osc:initiative"], "earthcode")
            self.assertEqual(coll["osc:project_website"], "https://project.example.org")
            self.assertEqual(coll["osc:project_description"], "Project description.")
            self.assertEqual(coll["osc:contract-number"], "4000114410/15/NL/BW")
            self.assertEqual(coll["sci:doi"], "10.1000/xyz123")
            self.assertIn("thumbnail", coll["assets"])
            self.assertEqual(coll["assets"]["thumbnail"]["roles"], ["thumbnail"])

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda *args, **kwargs: _make_dataset(),
    )
    def test_deprecated_dataset_status(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            config_path = self._write_config(tmp, osc_status=None)
            with open(config_path) as f:
                config = yaml.safe_load(f)
            del config["osc_status"]
            config["dataset_status"] = "planned"
            with open(config_path, "w") as f:
                yaml.safe_dump(config, f)
            generate_prr_collection(config_path, output_dir=out)
            with open(os.path.join(out, "tool-prr", "collection.json")) as f:
                coll = json.load(f)
            self.assertEqual(coll["osc:status"], "planned")

    def _assert_missing_raises(self, field: str):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            with open(config_path) as f:
                config = yaml.safe_load(f)
            del config[field]
            with open(config_path, "w") as f:
                yaml.safe_dump(config, f)
            with self.assertRaisesRegex(ValueError, f"{field} is required"):
                generate_prr_collection(config_path)

    def test_items_config_entry_missing_dataset_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(
                tmp, items_config=[{"item_id": "tool-item"}]
            )
            with self.assertRaisesRegex(
                ValueError, "dataset_id is required in items_config entry 0"
            ):
                generate_prr_collection(config_path)

    def test_missing_required_fields_raise(self):
        for field in (
            "collection_id",
            "osc_project",
            "osc_project_url",
            "license_type",
            "items_config",
        ):
            with self.subTest(field=field):
                self._assert_missing_raises(field)


if __name__ == "__main__":
    unittest.main()
