import os

import pytest
from unittest.mock import patch, MagicMock, mock_open

from deep_code.api.publish import ProductPublisher

class TestProductPublisher:

    @patch("deep_code.api.publish.fsspec.open")
    def test_init_missing_credentials(self, mock_fsspec_open):
        mock_fsspec_open.return_value.__enter__.return_value = mock_open(read_data="{}")()

        with pytest.raises(ValueError, match="GitHub credentials are missing in the git.yaml file."):
            ProductPublisher("/path/to/git.yaml")

    @patch("deep_code.utils.github_automation.GitHubAutomation")
    @patch("deep_code.api.publish.fsspec.open")
    def test_init_with_credentials(self, mock_fsspec_open):
        git_yaml_content = """
        github-username: test-user
        github-token: test-token
        """
        mock_fsspec_open.return_value.__enter__.return_value = mock_open(
            read_data=git_yaml_content)()

        publisher = ProductPublisher("/path/to/git.yaml")

        assert publisher.github_username == "test-user"
        assert publisher.github_token == "test-token"

    @patch("deep_code.api.publish.fsspec.open")
    def test_publish_product_missing_ids(self, mock_fsspec_open):
        git_yaml_content = """
        github-username: test-user
        github-token: test-token
        """
        dataset_yaml_content = """
        collection-id: test-collection
        """
        mock_fsspec_open.side_effect = [
            mock_open(read_data=git_yaml_content)(),
            mock_open(read_data=dataset_yaml_content)()
        ]

        publisher = ProductPublisher("/path/to/git.yaml")

        with pytest.raises(ValueError,
                           match="Dataset ID or Collection ID is missing in the "
                                 "dataset-config.yaml file."):
            publisher.publish_product("/path/to/dataset-config.yaml")

    @patch("os.makedirs")
    @patch("subprocess.run")
    @patch("requests.post")
    @patch("deep_code.utils.github_automation.GitHubAutomation")
    @patch("deep_code.api.publish.fsspec.open")
    def test_publish_product_success(self, mock_fsspec_open, mock_github_automation,
                                     mock_requests_post, mock_subprocess_run,
                                     mock_makedirs):
        git_yaml_content = """
        github-username: test-user
        github-token: test-token
        """
        dataset_yaml_content = """
        dataset-id: test-dataset
        collection-id: test-collection
        documentation-link: http://example.com/doc
        access-link: http://example.com/access
        dataset-status: ongoing
        dataset-region: Global
        dataset-theme: ["climate"]
        cf-parameter: []
        """
        mock_fsspec_open.side_effect = [
            mock_open(read_data=git_yaml_content)(),
            mock_open(read_data=dataset_yaml_content)()
        ]

        # Mock GitHubAutomation methods
        mock_git = mock_github_automation.return_value
        mock_git.fork_repository.return_value = None
        mock_git.clone_repository.return_value = None
        mock_git.create_branch.return_value = None
        mock_git.add_file.return_value = None
        mock_git.commit_and_push.return_value = None
        mock_git.create_pull_request.return_value = "http://example.com/pr"

        # Mock requests.post for GitHub API calls
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response

        # Mock subprocess.run for git commands
        mock_subprocess_run.return_value = None

        home_dir = os.path.expanduser("~")
        local_clone_dir = os.path.join(home_dir, "temp_repo")

        # Mock os.makedirs to avoid real directory creation
        mock_makedirs.return_value = None

        # Mock OSCProductSTACGenerator
        mock_collection = MagicMock()
        mock_collection.to_dict.return_value = {
            "type": "Collection",
            "id": "test-collection",
            "description": "A test STAC collection",
            "extent": {
                "spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]},
                "temporal": {"interval": [["2023-01-01T00:00:00Z", None]]},
            },
            "links": [],
            "stac_version": "1.0.0",
        }

        with patch("deep_code.api.publish.OSCProductSTACGenerator") as mock_generator:
            mock_generator.return_value.build_stac_collection.return_value = mock_collection

            publisher = ProductPublisher("/path/to/git.yaml")
            publisher.publish_product("/path/to/dataset-config.yaml")

            auth_url = "https://test-user:test-token@github.com/test-user/open-science-catalog-metadata-testing.git"
            mock_subprocess_run.assert_any_call(
                ["git", "clone", auth_url, local_clone_dir], check=True
            )

