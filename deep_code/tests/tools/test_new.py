import unittest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from deep_code.tools.new import RepositoryInitializer


class TestRepositoryInitializer(unittest.TestCase):
    def setUp(self):
        """Set up a temporary directory for testing."""
        self.test_repo_name = "test_repo"
        self.test_repo_dir = Path(self.test_repo_name).absolute()
        self.templates_dir = Path(__file__).parent.parent / "deep_code" / "templates"

        # Mock GitHub credentials
        self.github_username = "test_user"
        self.github_token = "test_token"

        # Ensure the repository directory does not exist before each test
        if self.test_repo_dir.exists():
            shutil.rmtree(self.test_repo_dir)

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        if self.test_repo_dir.exists():
            shutil.rmtree(self.test_repo_dir)

    @patch("deep_code.tools.new.read_git_access_file")
    def test_missing_github_credentials(self, mock_read_git_access_file):
        """Test that an error is raised if GitHub credentials are missing."""
        # Mock the Git access file with missing credentials
        mock_read_git_access_file.return_value = {}

        # Verify that an error is raised
        with self.assertRaises(ValueError) as context:
            RepositoryInitializer(self.test_repo_name)
        self.assertIn("GitHub credentials are missing", str(context.exception))

    @patch("deep_code.tools.new.read_git_access_file")
    def test_template_not_found(self, mock_read_git_access_file):
        """Test that an error is raised if a template file is missing."""
        # Mock the Git access file
        mock_read_git_access_file.return_value = {
            "github-username": self.github_username,
            "github-token": self.github_token,
        }

        # Initialize the repository with a non-existent template
        initializer = RepositoryInitializer(self.test_repo_name)
        initializer.templates_dir = Path("/non/existent/path")

        # Verify that an error is raised
        with self.assertRaises(FileNotFoundError):
            initializer.initialize()


if __name__ == "__main__":
    unittest.main()