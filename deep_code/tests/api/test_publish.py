import unittest
from unittest.mock import patch, MagicMock, mock_open
import yaml

from deep_code.api.publish import ProductPublisher


class TestProductPublisher(unittest.TestCase):
    @patch("fsspec.open")
    @patch("deep_code.utils.dataset_stac_generator.OSCProductSTACGenerator")
    @patch("deep_code.utils.github_automation.GitHubAutomation")
    def test_publish_product_success(
        self, mock_github_automation, mock_stac_generator, mock_fsspec_open
    ):
        # Mock the git.yaml configuration
        git_config = {"github-username": "test-user", "github-token": "test-token"}
        mock_fsspec_open.side_effect = [
            mock_open(read_data=yaml.dump(git_config)).return_value,
            mock_open(
                read_data=yaml.dump(
                    {
                        "dataset-id": "test-dataset",
                        "collection-id": "test-collection",
                        "documentation-link": "http://example.com/doc",
                        "access-link": "http://example.com/access",
                        "dataset-status": "active",
                        "dataset-region": "region-1",
                        "dataset-theme": ["theme-1", "theme-2"],
                    }
                )
            ).return_value,
        ]

        # Mock the STAC generator
        mock_generator_instance = mock_stac_generator.return_value
        mock_collection = MagicMock()
        mock_generator_instance.build_stac_collection.return_value = mock_collection

        # Mock the GitHub automation
        mock_github_instance = mock_github_automation.return_value

        # Create an instance of ProductPublisher
        publisher = ProductPublisher("path/to/git_config.yaml")
        publisher.github_automation = mock_github_instance

        # Call the publish_product method
        publisher.publish_product("path/to/dataset_config.yaml")

        # Assertions for GitHub automation
        mock_github_instance.fork_repository.assert_called_once()
        mock_github_instance.clone_repository.assert_called_once()
        mock_github_instance.create_branch.assert_called_once_with(
            "new-branch-name"
        )  # Replace with actual branch name
        mock_github_instance.add_file.assert_called_once_with(
            "products/test-collection/collection.json", mock_collection.to_dict()
        )
        mock_github_instance.commit_and_push.assert_called_once_with(
            "new-branch-name", "Add new collection: test-collection"
        )
        mock_github_instance.create_pull_request.assert_called_once_with(
            "new-branch-name",
            "Add new collection",
            "This PR adds a new collection to the repository.",
        )
        mock_github_instance.clean_up.assert_called_once()

        # Assertions for STAC generator
        mock_stac_generator.assert_called_once_with(
            dataset_id="test-dataset",
            collection_id="test-collection",
            documentation_link="http://example.com/doc",
            access_link="http://example.com/access",
            osc_status="active",
            osc_region="region-1",
            osc_themes=["theme-1", "theme-2"],
        )
        mock_generator_instance.build_stac_collection.assert_called_once()

    @patch("fsspec.open", mock_open(read_data="{}"))
    def test_publish_product_missing_config(self):
        # Test for missing dataset-id or collection-id
        with self.assertRaises(ValueError) as context:
            publisher = ProductPublisher("path/to/git_config.yaml")
            publisher.publish_product("path/to/dataset_config.yaml")
        self.assertEqual(
            str(context.exception),
            "Dataset ID or Collection ID is missing in the dataset-config.yaml file.",
        )

    def test_missing_git_credentials(self):
        # Test for missing GitHub credentials
        with patch("fsspec.open", mock_open(read_data="{}")):
            with self.assertRaises(ValueError) as context:
                ProductPublisher("path/to/git_config.yaml")
            self.assertEqual(
                str(context.exception),
                "GitHub credentials are missing in the git.yaml file.",
            )


if __name__ == "__main__":
    unittest.main()
