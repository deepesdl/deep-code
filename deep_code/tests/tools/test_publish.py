from unittest.mock import MagicMock, mock_open, patch

import pytest

from deep_code.tools.publish import DatasetPublisher


class TestDatasetPublisher:
    @patch("deep_code.tools.publish.fsspec.open")
    def test_init_missing_credentials(self, mock_fsspec_open):
        mock_fsspec_open.return_value.__enter__.return_value = mock_open(
            read_data="{}"
        )()

        with pytest.raises(
            ValueError, match="GitHub credentials are missing in the `.gitaccess` file."
        ):
            DatasetPublisher()

    @patch("deep_code.tools.publish.fsspec.open")
    def test_publish_dataset_missing_ids(self, mock_fsspec_open):
        git_yaml_content = """
        github-username: test-user
        github-token: test-token
        """
        dataset_yaml_content = """
        collection-id: test-collection
        """
        mock_fsspec_open.side_effect = [
            mock_open(read_data=git_yaml_content)(),
            mock_open(read_data=dataset_yaml_content)(),
        ]

        publisher = DatasetPublisher()

        with pytest.raises(
            ValueError, match="Dataset ID or Collection ID missing in the config."
        ):
            publisher.publish_dataset("/path/to/dataset-config.yaml")

    @patch("deep_code.utils.github_automation.os.chdir")
    @patch("deep_code.utils.github_automation.subprocess.run")
    @patch("deep_code.utils.github_automation.os.path.expanduser", return_value="/tmp")
    @patch("requests.post")
    @patch("deep_code.utils.github_automation.GitHubAutomation")
    @patch("deep_code.tools.publish.fsspec.open")
    def test_publish_dataset_success(
        self,
        mock_fsspec_open,
        mock_github_automation,
        mock_requests_post,
        mock_expanduser,
        mock_subprocess_run,
        mock_chdir,
    ):
        #  Mock the YAML reads
        git_yaml_content = """
             github-username: test-user
             github-token: test-token
             """
        dataset_yaml_content = """
             dataset_id: test-dataset
             collection_id: test-collection
             documentation_link: http://example.com/doc
             access_link: http://example.com/access
             dataset_status: ongoing
             dataset_region: Global
             osc_theme: ["climate"]
             cf_parameter: []
             """
        mock_fsspec_open.side_effect = [
            mock_open(read_data=git_yaml_content)(),
            mock_open(read_data=dataset_yaml_content)(),
        ]

        # Mock GitHubAutomation methods
        mock_git = mock_github_automation.return_value
        mock_git.fork_repository.return_value = None
        mock_git.clone_repository.return_value = None
        mock_git.create_branch.return_value = None
        mock_git.add_file.return_value = None
        mock_git.commit_and_push.return_value = None
        mock_git.create_pull_request.return_value = "http://example.com/pr"
        mock_git.clean_up.return_value = None

        # Mock subprocess.run & os.chdir
        mock_subprocess_run.return_value = None
        mock_chdir.return_value = None

        # Mock STAC generator
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
        with patch("deep_code.tools.publish.OscDatasetStacGenerator") as mock_generator:
            mock_generator.return_value.build_dataset_stac_collection.return_value = (
                mock_collection
            )

            # Instantiate & publish
            publisher = DatasetPublisher()
            publisher.publish_dataset("/fake/path/to/dataset-config.yaml")

        # Assert that we called git clone with /tmp/temp_repo
        # Because expanduser("~") is now patched to /tmp, the actual path is /tmp/temp_repo
        auth_url = "https://test-user:test-token@github.com/test-user/open-science-catalog-metadata-testing.git"
        mock_subprocess_run.assert_any_call(
            ["git", "clone", auth_url, "/tmp/temp_repo"], check=True
        )

        # Also confirm we changed directories to /tmp/temp_repo
        mock_chdir.assert_any_call("/tmp/temp_repo")
