#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import os
import unittest
from unittest.mock import MagicMock, call, patch

import xarray
import xarray as xr

from deep_code.utils.helper import open_dataset


def make_dummy_dataset():
    """Create a simple xarray.Dataset for testing."""
    return xr.Dataset(
        coords={"time": [0, 1, 2]}, data_vars={"x": (("time",), [10, 20, 30])}
    )


class TestOpenDataset(unittest.TestCase):
    @patch("deep_code.utils.helper.logging.getLogger")
    @patch("deep_code.utils.helper.new_data_store")
    def test_success_public_store(self, mock_new_store, mock_get_logger):
        """Should open dataset with the public store on first try."""
        dummy = make_dummy_dataset()
        mock_store = MagicMock()
        mock_store.open_data.return_value = dummy
        mock_new_store.return_value = mock_store
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = open_dataset("test-id")

        self.assertIs(result, dummy)
        mock_new_store.assert_called_once_with(
            "s3", root="deep-esdl-public", storage_options={"anon": True}
        )
        mock_logger.info.assert_any_call(
            "Attempting to open dataset 'test-id' with configuration: Public store"
        )
        mock_logger.info.assert_any_call(
            "Successfully opened dataset 'test-id' with configuration: Public store"
        )

    @patch("deep_code.utils.helper.new_data_store")
    @patch("deep_code.utils.helper.logging.getLogger")
    def test_open_dataset_success_authenticated_store(
        self, mock_get_logger, mock_new_store
    ):
        """Test fallback to authenticated store when public store fails."""
        mock_store = MagicMock()
        mock_new_store.side_effect = [Exception("Public store failure"), mock_store]
        mock_store.open_data.return_value = make_dummy_dataset()

        os.environ["S3_USER_STORAGE_BUCKET"] = "mock-bucket"
        os.environ["S3_USER_STORAGE_KEY"] = "mock-key"
        os.environ["S3_USER_STORAGE_SECRET"] = "mock-secret"

        ds = open_dataset("my-id", logger=mock_get_logger())

        self.assertIsInstance(ds, xarray.Dataset)

        # And new_data_store should have been called twice with exactly these params
        expected_calls = [
            call("s3", root="deep-esdl-public", storage_options={"anon": True}),
            call(
                "s3",
                root="mock-bucket",
                storage_options={
                    "anon": False,
                    "key": "mock-key",
                    "secret": "mock-secret",
                },
            ),
        ]
        mock_new_store.assert_has_calls(expected_calls, any_order=False)

        # And the logger should have info about both attempts
        logger = mock_get_logger()
        logger.info.assert_any_call(
            "Attempting to open dataset 'my-id' with configuration: Public store"
        )
        logger.info.assert_any_call(
            "Attempting to open dataset 'my-id' with configuration: Authenticated store"
        )
        logger.info.assert_any_call(
            "Successfully opened dataset 'my-id' with configuration: Authenticated store"
        )

    @patch("deep_code.utils.helper.logging.getLogger")
    @patch("deep_code.utils.helper.new_data_store")
    def test_all_stores_fail_raises(self, mock_new_store, mock_get_logger):
        """Should raise ValueError if all stores fail."""
        mock_new_store.side_effect = Exception("fail")
        os.environ["S3_USER_STORAGE_BUCKET"] = "user-bucket"
        os.environ["S3_USER_STORAGE_KEY"] = "key"
        os.environ["S3_USER_STORAGE_SECRET"] = "secret"
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with self.assertRaises(ValueError) as ctx:
            open_dataset("test-id")
        msg = str(ctx.exception)
        self.assertIn("Tried configurations: Public store, Authenticated store", msg)
        self.assertIn("Last error: fail", msg)

    @patch("deep_code.utils.helper.logging.getLogger")
    @patch("deep_code.utils.helper.new_data_store")
    def test_with_custom_configs(self, mock_new_store, mock_get_logger):
        """Should use provided storage_configs instead of defaults."""
        dummy = make_dummy_dataset()
        mock_store = MagicMock()
        mock_store.open_data.return_value = dummy
        mock_new_store.return_value = mock_store
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        custom_cfgs = [
            {
                "description": "Local store",
                "params": {"storage_type": "file", "root": ".", "storage_options": {}},
            }
        ]

        result = open_dataset("test-id", storage_configs=custom_cfgs)

        self.assertIs(result, dummy)
        mock_new_store.assert_called_once_with("file", root=".", storage_options={})
        mock_logger.info.assert_any_call(
            "Attempting to open dataset 'test-id' with configuration: Local store"
        )
        mock_logger.info.assert_any_call(
            "Successfully opened dataset 'test-id' with configuration: Local store"
        )

    @patch("deep_code.utils.helper.logging.getLogger")
    @patch("deep_code.utils.helper.new_data_store")
    def test_uses_provided_logger(self, mock_new_store, mock_get_logger):
        """Should use the logger provided by the caller."""
        dummy = make_dummy_dataset()
        mock_store = MagicMock()
        mock_store.open_data.return_value = dummy
        mock_new_store.return_value = mock_store
        custom_logger = MagicMock()
        mock_get_logger.side_effect = AssertionError("getLogger should not be used")

        result = open_dataset("test-id", logger=custom_logger)

        self.assertIs(result, dummy)
        custom_logger.info.assert_any_call(
            "Attempting to open dataset 'test-id' with configuration: Public store"
        )
        custom_logger.info.assert_any_call(
            "Successfully opened dataset 'test-id' with configuration: Public store"
        )
