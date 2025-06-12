# Copyright © 2025 Brockmann Consult GmbH.
# This software is distributed under the terms and conditions of the
# MIT license (https://mit-license.org/).

import unittest

import xarray as xr
from xrlint.testing import RuleTest, RuleTester

from deep_code.utils.custom_xrlint_rules import (
    DatasetDescriptionRule,
    VariableGcmdKeywordUrlRule,
)


class TestDeepCodePlugin(unittest.TestCase):
    def setUp(self):
        """Set up test datasets."""
        # Valid dataset with all required metadata
        self.valid_dataset = xr.Dataset(
            data_vars={
                "temperature": (("time", "lat", "lon"), [[[300, 301], [302, 303]]]),
                "precipitation": (("time", "lat", "lon"), [[[10, 20], [30, 40]]]),
            },
            coords={"time": [1], "lat": [0, 1], "lon": [0, 1]},
            attrs={
                "description": "Test climate dataset",
                "title": "Climate Dataset 2025",
            },
        )
        self.valid_dataset["temperature"].attrs[
            "gcmd_keyword_url"
        ] = "https://gcmd.nasa.gov/KeywordViewer/temperature"
        self.valid_dataset["temperature"].attrs["units"] = "K"
        self.valid_dataset["precipitation"].attrs[
            "gcmd_keyword_url"
        ] = "https://gcmd.nasa.gov/KeywordViewer/precipitation"
        self.valid_dataset["precipitation"].attrs["units"] = "mm"

        # Invalid dataset missing required metadata
        self.invalid_dataset = xr.Dataset(
            data_vars={
                "temperature": (("time", "lat", "lon"), [[[300, 301], [302, 303]]]),
                "precipitation": (("time", "lat", "lon"), [[[10, 20], [30, 40]]]),
            },
            coords={"time": [1], "lat": [0, 1], "lon": [0, 1]},
            attrs={},
        )
        self.invalid_dataset["temperature"].attrs[
            "gcmd_keyword_url"
        ] = "https://gcmd.nasa.gov/KeywordViewer/temperature"
        self.invalid_dataset["temperature"].attrs["units"] = "K"
        # Intentionally omit gcmd_keyword_url and units for precipitation

        self.tester = RuleTester()

    def test_dataset_description(self):
        """Test DatasetDescriptionRule with valid and invalid dataset."""
        self.tester.run(
            "dataset-description",
            DatasetDescriptionRule,
            valid=[RuleTest(dataset=self.valid_dataset)],
            invalid=[RuleTest(dataset=self.invalid_dataset, expected=1)],
        )

    def test_variable_gcmd_keyword_url(self):
        """Test VariableGcmdKeywordUrlRule with valid dataset."""
        self.tester.run(
            "variable-gcmd-keyword-url",
            VariableGcmdKeywordUrlRule,
            valid=[RuleTest(dataset=self.valid_dataset)],
            invalid=[RuleTest(dataset=self.invalid_dataset, expected=1)],
        )
