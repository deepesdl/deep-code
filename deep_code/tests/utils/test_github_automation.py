import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from deep_code.utils.github_automation import GitHubAutomation


class TestGitHubAutomation(unittest.TestCase):
    def setUp(self):
        # Set up test data
        self.username = "testuser"
        self.token = "testtoken"
        self.repo_owner = "testowner"
        self.repo_name = "testrepo"
        self.github_automation = GitHubAutomation(
            self.username, self.token, self.repo_owner, self.repo_name
        )
        logging.disable(logging.CRITICAL)  # Disable logging during tests

    def tearDown(self):
        logging.disable(logging.NOTSET)  # Re-enable logging after tests

    @patch("requests.post")
    def test_fork_repository(self, mock_post):
        # Mock the response from GitHub API
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Call the method
        self.github_automation.fork_repository()

        # Assertions
        mock_post.assert_called_once_with(
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/forks",
            headers={"Authorization": f"token {self.token}"},
        )

    @patch("subprocess.run")
    def test_clone_repository_new(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.path.exists to return False (directory does not exist)
        with patch("os.path.exists", return_value=False):
            self.github_automation.clone_sync_repository()

        # Assertions
        mock_run.assert_called_once_with(
            [
                "git",
                "clone",
                f"https://{self.username}:{self.token}@github.com/{self.username}/{self.repo_name}.git",
                self.github_automation.local_clone_dir,
            ],
            check=True,
        )

    @patch("subprocess.run")
    def test_clone_repository_existing(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.path.exists to return True (directory exists)
        with patch("os.path.exists", return_value=True):
            with patch("os.chdir"):
                self.github_automation.clone_sync_repository()

        # Assertions
        mock_run.assert_called_once_with(["git", "pull"], check=True)

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.chdir
        with patch("os.chdir"):
            self.github_automation.create_branch("test-branch")

        # Assertions
        mock_run.assert_called_once_with(
            ["git", "checkout", "-b", "test-branch"], check=True
        )

    @patch("subprocess.run")
    def test_add_file(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.chdir and Path
        with patch("os.chdir"), patch("pathlib.Path.mkdir"), patch(
            "builtins.open", unittest.mock.mock_open()
        ):
            self.github_automation.add_file("test/file.json", {"key": "value"})

        # Assertions
        mock_run.assert_called_once_with(
            [
                "git",
                "add",
                str(Path(self.github_automation.local_clone_dir) / "test/file.json"),
            ],
            check=True,
        )

    @patch("subprocess.run")
    def test_commit_and_push(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.chdir
        with patch("os.chdir"):
            self.github_automation.commit_and_push("test-branch", "Test commit message")

        # Assertions
        mock_run.assert_any_call(
            ["git", "commit", "-m", "Test commit message"], check=True
        )
        mock_run.assert_any_call(
            ["git", "push", "-u", "origin", "test-branch"], check=True
        )

    @patch("requests.post")
    def test_create_pull_request(self, mock_post):
        # Mock the response from GitHub API
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"html_url": "https://github.com/test/pull/1"}
        mock_post.return_value = mock_response

        # Mock os.chdir
        with patch("os.chdir"):
            self.github_automation.create_pull_request(
                "test-branch", "Test PR", "Test body"
            )

        # Assertions
        mock_post.assert_called_once_with(
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls",
            headers={"Authorization": f"token {self.token}"},
            json={
                "title": "Test PR",
                "head": f"{self.username}:test-branch",
                "base": "main",
                "body": "Test body",
            },
        )

    @patch("subprocess.run")
    def test_clean_up(self, mock_run):
        # Mock the subprocess.run method
        mock_run.return_value = MagicMock()

        # Mock os.chdir
        with patch("os.chdir"):
            self.github_automation.clean_up()

        # Assertions
        mock_run.assert_called_once_with(
            ["rm", "-rf", self.github_automation.local_clone_dir]
        )

    def test_file_exists(self):
        # Mock os.path.isfile
        with patch("os.path.isfile", return_value=True):
            result = self.github_automation.file_exists("test/file.json")

        # Assertions
        self.assertTrue(result)
