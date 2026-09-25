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
        attrs={"description": "PRR tool test cube"},
    )


class TestGeneratePrrCollection(unittest.TestCase):
    def _write_config(self, tmp, **overrides):
        config = {
            "dataset_id": "test.zarr",
            "collection_id": "tool-prr",
            "license_type": "CC-BY-4.0",
            "access_link": "s3://bucket/test.zarr",
            "dataset_status": "ongoing",
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
        side_effect=lambda dataset_id, logger=None: _make_dataset(),
    )
    def test_writes_collection_tree(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            out = os.path.join(tmp, "out")
            result = generate_prr_collection(config_path, output_dir=out)

            self.assertEqual(result, out)
            self.assertTrue(os.path.isfile(os.path.join(out, "collection.json")))
            self.assertTrue(
                os.path.isfile(os.path.join(out, "tool-prr", "tool-prr.json"))
            )
            with open(os.path.join(out, "collection.json")) as f:
                coll = json.load(f)
            self.assertEqual(coll["id"], "tool-prr")
            self.assertEqual(coll["type"], "Collection")
            self.assertEqual(coll["osc:type"], "product")

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda dataset_id, logger=None: _make_dataset(),
    )
    def test_default_output_dir_from_collection_id(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = self._write_config(tmp)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                out = generate_prr_collection(config_path)
                self.assertEqual(out, "prr/tool-prr")
                self.assertTrue(os.path.isfile(os.path.join(out, "collection.json")))
            finally:
                os.chdir(cwd)

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda dataset_id, logger=None: _make_dataset(),
    )
    def test_output_dir_from_config(self, _mock_open_ds):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "from-config")
            config_path = self._write_config(tmp, prr_output_dir=out)
            result = generate_prr_collection(config_path)
            self.assertEqual(result, out)
            self.assertTrue(os.path.isfile(os.path.join(out, "collection.json")))

    @patch(
        "deep_code.utils.dataset_stac_generator.open_dataset",
        side_effect=lambda dataset_id, logger=None: _make_dataset(),
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
            with open(os.path.join(out, "collection.json")) as f:
                coll = json.load(f)
            self.assertEqual(coll["osc:initiative"], "earthcode")
            self.assertEqual(coll["osc:project_website"], "https://project.example.org")
            self.assertEqual(coll["osc:project_description"], "Project description.")
            self.assertEqual(coll["osc:contract-number"], "4000114410/15/NL/BW")
            self.assertEqual(coll["sci:doi"], "10.1000/xyz123")
            self.assertIn("thumbnail", coll["assets"])
            self.assertEqual(coll["assets"]["thumbnail"]["roles"], ["thumbnail"])

    def test_missing_license_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "cfg.yaml")
            with open(config_path, "w") as f:
                yaml.safe_dump({"dataset_id": "test.zarr", "collection_id": "c"}, f)
            with self.assertRaisesRegex(ValueError, "license_type is required"):
                generate_prr_collection(config_path)

    def test_missing_ids_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "cfg.yaml")
            with open(config_path, "w") as f:
                yaml.safe_dump({"license_type": "CC-BY-4.0"}, f)
            with self.assertRaisesRegex(ValueError, "dataset_id.*collection_id"):
                generate_prr_collection(config_path)


if __name__ == "__main__":
    unittest.main()
