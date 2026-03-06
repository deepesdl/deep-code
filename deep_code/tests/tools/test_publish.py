import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml
from pystac import Catalog

from deep_code.tools.publish import Publisher
from deep_code.utils.ogc_api_record import LinksBuilder


class TestPublisher(unittest.TestCase):
    @patch("fsspec.open")
    @patch("deep_code.tools.publish.GitHubPublisher")
    def setUp(self, mock_github_publisher, mock_fsspec_open):
        # Mock GitHubPublisher to avoid reading .gitaccess
        self.mock_github_publisher_instance = MagicMock()
        mock_github_publisher.return_value = self.mock_github_publisher_instance

        # Mock dataset and workflow config files
        self.dataset_config = {
            "collection_id": "test-collection",
            "dataset_id": "test-dataset",
        }
        self.workflow_config = {
            "properties": {"title": "Test Workflow"},
            "workflow_id": "test-workflow",
        }

        # Mock fsspec.open for config files
        self.mock_fsspec_open = mock_fsspec_open
        self.mock_fsspec_open.side_effect = [
            mock_open(read_data=yaml.dump(self.dataset_config)).return_value,
            mock_open(read_data=yaml.dump(self.workflow_config)).return_value,
        ]

        # Initialize Publisher
        self.publisher = Publisher(
            dataset_config_path="test-dataset-config.yaml",
            workflow_config_path="test-workflow-config.yaml",
        )

    def test_normalize_name(self):
        self.assertEqual(Publisher._normalize_name("Test Name"), "test-name")
        self.assertEqual(Publisher._normalize_name("Test   Name"), "test---name")
        self.assertIsNone(Publisher._normalize_name(""))
        self.assertIsNone(Publisher._normalize_name(None))

    def test_write_to_file(self):
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = temp_file.name

        # Test data
        data = {"key": "value"}

        # Call the method
        Publisher._write_to_file(file_path, data)

        # Read the file and verify its content
        with open(file_path, "r") as f:
            content = json.load(f)
            self.assertEqual(content, data)

        # Clean up
        Path(file_path).unlink()

    def test_update_base_catalog(self):
        # Create a mock Catalog
        catalog = Catalog(id="test-catalog", description="Test Catalog")

        # Mock file path and item ID
        catalog_path = "test-catalog.json"
        item_id = "test-item"
        self_href = "https://example.com/catalog.json"

        self.publisher.workflow_title = "Test Workflow"

        # Mock the Catalog.from_file method
        with patch("pystac.Catalog.from_file", return_value=catalog):
            updated_catalog = self.publisher._update_base_catalog(
                catalog_path, item_id, self_href
            )

        # Assertions
        self.assertEqual(updated_catalog.get_self_href(), self_href)
        self.assertIsInstance(updated_catalog, Catalog)

    def test_read_config_files(self):
        # Mock dataset and workflow config files
        dataset_config = {
            "collection_id": "test-collection",
            "dataset_id": "test-dataset",
        }
        workflow_config = {
            "properties": {"title": "Test Workflow"},
            "workflow_id": "test-workflow",
        }

        # Mock fsspec.open for config files
        self.mock_fsspec_open.side_effect = [
            mock_open(read_data=yaml.dump(dataset_config)).return_value,
            mock_open(read_data=yaml.dump(workflow_config)).return_value,
        ]

        # Assertions
        self.assertEqual(self.publisher.dataset_config, dataset_config)
        self.assertEqual(self.publisher.workflow_config, workflow_config)

    @patch("deep_code.tools.publish.GitHubPublisher")
    def test_environment_repo_selection(self, mock_gp):
        Publisher(environment="production")
        assert mock_gp.call_args.kwargs["repo_name"] == "open-science-catalog-metadata"
        Publisher(environment="staging")
        assert (
            mock_gp.call_args.kwargs["repo_name"]
            == "open-science-catalog-metadata-staging"
        )
        Publisher(environment="testing")
        assert (
            mock_gp.call_args.kwargs["repo_name"]
            == "open-science-catalog-metadata-testing"
        )

    @patch.object(Publisher, "publish_dataset", return_value={"a": {}})
    @patch.object(
        Publisher, "generate_workflow_experiment_records", return_value={"b": {}}
    )
    def test_publish_mode_routing(self, mock_wf, mock_ds):
        # dataset only
        self.publisher.publish(write_to_file=True, mode="dataset")
        mock_ds.assert_called()
        mock_wf.assert_not_called()

        mock_ds.reset_mock()
        mock_wf.reset_mock()
        self.publisher.publish(write_to_file=True, mode="workflow")
        mock_ds.assert_not_called()
        mock_wf.assert_called()

    @patch.object(Publisher, "generate_workflow_experiment_records", return_value={})
    @patch.object(Publisher, "publish_dataset", return_value={})
    def test_publish_nothing_to_publish_raises(
        self, mock_publish_dataset, mock_generate_workflow_experiment_records
    ):
        with pytest.raises(ValueError):
            self.publisher.publish(write_to_file=False, mode="dataset")
        mock_publish_dataset.assert_called_once()
        mock_generate_workflow_experiment_records.assert_not_called()

    @patch.object(Publisher, "publish_dataset", return_value={"x": {}})
    @patch.object(
        Publisher, "generate_workflow_experiment_records", return_value={"y": {}}
    )
    def test_publish_builds_pr_params(self, mock_wf, mock_ds):
        # Make PR creation return a fixed URL
        self.publisher.gh_publisher.publish_files.return_value = "PR_URL"

        # Provide IDs for commit/PR labels
        self.publisher.collection_id = "col"
        self.publisher.workflow_id = "wf"

        url = self.publisher.publish(write_to_file=False, mode="all")
        assert url == "PR_URL"

        # Inspect the call arguments to publish_files
        _, kwargs = self.publisher.gh_publisher.publish_files.call_args
        assert "dataset: col" in kwargs["commit_message"]
        assert "workflow/experiment: wf" in kwargs["commit_message"]
        assert "dataset: col" in kwargs["pr_title"]
        assert "workflow/experiment: wf" in kwargs["pr_title"]


    # ------------------------------------------------------------------
    # S3 credential resolution
    # ------------------------------------------------------------------

    def test_get_stac_s3_storage_options_prefers_xcube_env_vars(self):
        env = {
            "S3_USER_STORAGE_KEY": "xcube-key",
            "S3_USER_STORAGE_SECRET": "xcube-secret",
            "AWS_ACCESS_KEY_ID": "aws-key",
            "AWS_SECRET_ACCESS_KEY": "aws-secret",
        }
        with patch.dict(os.environ, env):
            opts = self.publisher._get_stac_s3_storage_options()
        self.assertEqual(opts["key"], "xcube-key")
        self.assertEqual(opts["secret"], "xcube-secret")

    def test_get_stac_s3_storage_options_falls_back_to_aws_env_vars(self):
        env = {"AWS_ACCESS_KEY_ID": "aws-key", "AWS_SECRET_ACCESS_KEY": "aws-secret"}
        # Ensure xcube vars are absent
        patched_env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("S3_USER_STORAGE_KEY", "S3_USER_STORAGE_SECRET")
        }
        patched_env.update(env)
        with patch.dict(os.environ, patched_env, clear=True):
            opts = self.publisher._get_stac_s3_storage_options()
        self.assertEqual(opts["key"], "aws-key")
        self.assertEqual(opts["secret"], "aws-secret")

    def test_get_stac_s3_storage_options_returns_empty_for_boto3_chain(self):
        no_cred_env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "S3_USER_STORAGE_KEY",
                "S3_USER_STORAGE_SECRET",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
            )
        }
        with patch.dict(os.environ, no_cred_env, clear=True):
            opts = self.publisher._get_stac_s3_storage_options()
        self.assertEqual(opts, {})

    # ------------------------------------------------------------------
    # S3 write helper
    # ------------------------------------------------------------------

    @patch("deep_code.tools.publish.fsspec.open")
    def test_write_stac_catalog_to_s3(self, mock_fsspec_open):
        mock_file = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_file)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_fsspec_open.return_value = mock_ctx

        file_dict = {
            "s3://bucket/catalog.json": {"type": "Catalog", "id": "test"},
            "s3://bucket/col/item.json": {"type": "Feature", "id": "item"},
        }
        self.publisher._write_stac_catalog_to_s3(
            file_dict, {"key": "k", "secret": "s"}
        )

        self.assertEqual(mock_fsspec_open.call_count, 2)
        mock_fsspec_open.assert_any_call(
            "s3://bucket/catalog.json", "w", key="k", secret="s"
        )
        mock_fsspec_open.assert_any_call(
            "s3://bucket/col/item.json", "w", key="k", secret="s"
        )

    # ------------------------------------------------------------------
    # End-to-end zarr STAC publishing wired into publish()
    # ------------------------------------------------------------------

    @patch("deep_code.tools.publish.fsspec.open")
    @patch.object(Publisher, "publish_dataset", return_value={"github_file.json": {}})
    def test_publish_writes_zarr_stac_to_s3_when_configured(
        self, mock_publish_ds, mock_fsspec_open
    ):
        self.publisher.dataset_config["stac_catalog_s3_root"] = (
            "s3://test-bucket/stac/"
        )

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_fsspec_open.return_value = mock_ctx

        mock_generator = MagicMock()
        mock_generator.build_zarr_stac_catalog_file_dict.return_value = {
            "s3://test-bucket/stac/catalog.json": {"type": "Catalog"},
            "s3://test-bucket/stac/test-collection/item.json": {"type": "Feature"},
        }
        # Simulate what publish_dataset() normally does: store the generator
        self.publisher._last_generator = mock_generator
        self.publisher.gh_publisher.publish_files.return_value = "PR_URL"

        self.publisher.publish(mode="dataset")

        mock_generator.build_zarr_stac_catalog_file_dict.assert_called_once_with(
            "s3://test-bucket/stac/"
        )
        # Two S3 files written: catalog.json + item.json
        self.assertEqual(mock_fsspec_open.call_count, 2)

    @patch.object(Publisher, "publish_dataset", return_value={"github_file.json": {}})
    def test_publish_skips_zarr_stac_when_not_configured(self, mock_publish_ds):
        # No stac_catalog_s3_root in config
        self.publisher.dataset_config = {
            "collection_id": "test-collection",
            "dataset_id": "test-dataset",
        }
        self.publisher.gh_publisher.publish_files.return_value = "PR_URL"

        with patch.object(
            self.publisher, "_write_stac_catalog_to_s3"
        ) as mock_write:
            self.publisher.publish(mode="dataset")
            mock_write.assert_not_called()


class TestParseGithubNotebookUrl:
    @pytest.mark.parametrize(
        "url,repo_url,repo_name,branch,file_path",
        [
            (
                "https://github.com/deepesdl/cube-gen/blob/main/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
                "https://github.com/deepesdl/cube-gen",
                "cube-gen",
                "main",
                "Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
            ),
            (
                "https://github.com/deepesdl/cube-gen/tree/release-1.0/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
                "https://github.com/deepesdl/cube-gen",
                "cube-gen",
                "release-1.0",
                "Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
            ),
            (
                "https://raw.githubusercontent.com/deepesdl/cube-gen/main/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
                "https://github.com/deepesdl/cube-gen",
                "cube-gen",
                "main",
                "Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb",
            ),
        ],
    )
    def test_valid_urls(self, url, repo_url, repo_name, branch, file_path):
        got_repo_url, got_repo_name, got_branch, got_file_path = LinksBuilder._parse_github_notebook_url(
            url
        )
        assert got_repo_url == repo_url
        assert got_repo_name == repo_name
        assert got_branch == branch
        assert got_file_path == file_path

    def test_invalid_domain(self):
        url = "https://gitlab.com/deepesdl/cube-gen/-/blob/main/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb"
        with pytest.raises(ValueError) as e:
            LinksBuilder._parse_github_notebook_url(url)
        assert "Only GitHub URLs are supported" in str(e.value)

    def test_unexpected_github_format_missing_blob_or_tree(self):
        # Missing the "blob" or "tree" segment
        url = "https://github.com/deepesdl/cube-gen/main/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb"
        with pytest.raises(ValueError) as e:
            LinksBuilder._parse_github_notebook_url(url)
        assert "Unexpected GitHub URL format" in str(e.value)

    def test_unexpected_raw_format_too_short(self):
        url = "https://raw.githubusercontent.com/deepesdl/cube-gen/main"
        with pytest.raises(ValueError) as e:
            LinksBuilder._parse_github_notebook_url(url)
        assert "Unexpected raw.githubusercontent URL format" in str(e.value)
