#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import os
import tempfile
import unittest


from deep_code.tools.new import TemplateGenerator


class TestTemplateGenerator(unittest.TestCase):
    def test_generate_dataset_template_writes_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            TemplateGenerator.generate_dataset_template(output_path=path)
            with open(path) as f:
                content = f.read()
        finally:
            os.unlink(path)

        # Required fields present
        self.assertIn("dataset_id", content)
        self.assertIn("collection_id", content)
        self.assertIn("license_type", content)
        self.assertIn("stac_catalog_s3_root", content)
        # Optional fields present
        self.assertIn("osc_themes", content)
        self.assertIn("visualisation_link", content)
        self.assertIn("osc_project_title", content)
        # Section headers
        self.assertIn("REQUIRED", content)
        self.assertIn("OPTIONAL", content)

    def test_generate_workflow_template_writes_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            TemplateGenerator.generate_workflow_template(output_path=path)
            with open(path) as f:
                content = f.read()
        finally:
            os.unlink(path)

        # Required fields present
        self.assertIn("workflow_id", content)
        self.assertIn("title", content)
        self.assertIn("license", content)
        # Optional fields present
        self.assertIn("jupyter_notebook_url", content)
        self.assertIn("contact", content)
        # Section headers
        self.assertIn("REQUIRED", content)
        self.assertIn("OPTIONAL", content)

    def test_generate_dataset_template_no_path_returns_none(self):
        result = TemplateGenerator.generate_dataset_template()
        self.assertIsNone(result)

    def test_generate_workflow_template_no_path_returns_none(self):
        result = TemplateGenerator.generate_workflow_template()
        self.assertIsNone(result)
