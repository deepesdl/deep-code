import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from deep_code.utils.github_automation import GitHubAutomation


class TestGitHubAutomation(unittest.TestCase):
    def setUp(self):
        self.github = GitHubAutomation(
            username="test-user",
            token="test-token",
            repo_owner="test-owner",
            repo_name="test-repo",
        )

    @patch("requests.post")
    def test_fork_repository(self, mock_post):
        """Test the fork_repository method."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.github.fork_repository()

        mock_post.assert_called_once_with(
            "https://api.github.com/repos/test-owner/test-repo/forks",
            headers={"Authorization": "token test-token"},
        )

    @patch("subprocess.run")
    @patch("os.chdir")
    def test_clone_repository(self, mock_chdir, mock_run):
        """Test the clone_repository method."""
        self.github.clone_repository()

        mock_run.assert_called_once_with(
            ["git", "clone", self.github.fork_repo_url, self.github.local_clone_dir],
            check=True,
        )
        mock_chdir.assert_called_once_with(self.github.local_clone_dir)

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        """Test the create_branch method."""
        branch_name = "test-branch"
        self.github.create_branch(branch_name)

        mock_run.assert_called_once_with(
            ["git", "checkout", "-b", branch_name], check=True
        )

    @patch("subprocess.run")
    @patch("builtins.open", new_callable=unittest.mock.mock_open)
    @patch("pathlib.Path.mkdir")
    def test_add_file(self, mock_mkdir, mock_open, mock_run):
        """Test the add_file method."""
        file_path = "test-dir/test-file.json"
        content = {"key": "value"}

        self.github.add_file(file_path, content)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_open.assert_called_once_with(
            Path(self.github.local_clone_dir) / file_path, "w"
        )
        mock_open().write.assert_called_once_with(json.dumps(content, indent=2))
        mock_run.assert_called_once_with(
            ["git", "add", str(Path(self.github.local_clone_dir) / file_path)],
            check=True,
        )

    @patch("subprocess.run")
    def test_commit_and_push(self, mock_run):
        """Test the commit_and_push method."""
        branch_name = "test-branch"
        commit_message = "Test commit message"

        self.github.commit_and_push(branch_name, commit_message)

        mock_run.assert_any_call(["git", "commit", "-m", commit_message], check=True)
        mock_run.assert_any_call(
            ["git", "push", "-u", "origin", branch_name], check=True
        )

    @patch("requests.post")
    def test_create_pull_request(self, mock_post):
        """Test the create_pull_request method."""
        branch_name = "test-branch"
        pr_title = "Test PR"
        pr_body = "This is a test PR"
        base_branch = "main"

        mock_response = MagicMock()
        mock_response.json.return_value = {"html_url": "https://github.com/test-pr"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.github.create_pull_request(branch_name, pr_title, pr_body, base_branch)

        mock_post.assert_called_once_with(
            "https://api.github.com/repos/test-owner/test-repo/pulls",
            headers={"Authorization": "token test-token"},
            json={
                "title": pr_title,
                "head": f"test-user:{branch_name}",
                "base": base_branch,
                "body": pr_body,
            },
        )

    @patch("subprocess.run")
    @patch("os.chdir")
    def test_clean_up(self, mock_chdir, mock_run):
        """Test the clean_up method."""
        self.github.clean_up()

        mock_chdir.assert_called_once_with("..")
        mock_run.assert_called_once_with(["rm", "-rf", self.github.local_clone_dir])


if __name__ == "__main__":
    unittest.main()
