import json
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
