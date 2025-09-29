import logging
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from deep_code.utils.github_automation import GitHubAutomation


def make_cp(stdout: str = ""):
    """Helper to mimic subprocess.CompletedProcess-like return for our mocks."""
    m = MagicMock()
    m.stdout = stdout
    return m


class TestGitHubAutomation(unittest.TestCase):
    def setUp(self):
        self.username = "testuser"
        self.token = "testtoken"
        self.repo_owner = "testowner"
        self.repo_name = "testrepo"
        self.gha = GitHubAutomation(
            self.username,
            self.token,
            self.repo_owner,
            self.repo_name,
            local_clone_dir="/tmp/temp_repo",
        )
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch("requests.post")
    def test_fork_repository(self, mock_post):
        mock_post.return_value = MagicMock(**{"raise_for_status.return_value": None})
        self.gha.fork_repository()

        mock_post.assert_called_once_with(
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/forks",
            headers={"Authorization": f"token {self.token}"},
            timeout=60,
        )

    @patch("subprocess.run")
    def test_clone_sync_repository_new(self, mock_run):
        """
        No .git directory → we clone and then ensure upstream remote gets added.
        """
        # Simulate: "git remote -v" returns nothing so we add 'upstream'
        def run_side_effect(args, cwd, check, capture_output=False, text=True):
            if args[:3] == ["git", "remote", "-v"]:
                return make_cp(stdout="")
            return make_cp()

        mock_run.side_effect = run_side_effect

        with patch.object(Path, "mkdir") as _mk, patch(
            "pathlib.Path.exists", side_effect=lambda p=None: False
        ):
            self.gha.clone_sync_repository()

        # Expect a clone, then a 'git remote -v', then 'git remote add upstream ...'
        origin_url = f"https://{self.username}:{self.token}@github.com/{self.username}/{self.repo_name}.git"

        expected_calls = [
            # git clone <origin_url> /tmp/temp_repo (cwd=".")
            call(
                ["git", "clone", origin_url, "/tmp/temp_repo"],
                cwd=".",
                check=True,
                capture_output=False,
                text=True,
            ),
            # ensure_upstream_remote -> remote -v (capture_output=True)
            call(
                ["git", "remote", "-v"],
                cwd="/tmp/temp_repo",
                check=True,
                capture_output=True,
                text=True,
            ),
            # since not present -> add upstream
            call(
                [
                    "git",
                    "remote",
                    "add",
                    "upstream",
                    f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
                ],
                cwd="/tmp/temp_repo",
                check=True,
                capture_output=False,
                text=True,
            ),
        ]
        # Only assert these key calls occurred in order (there can be other internal calls)
        mock_run.assert_has_calls(expected_calls, any_order=False)

    @patch("subprocess.run")
    def test_clone_sync_repository_existing(self, mock_run):
        """
        .git exists → we fetch/prune and still ensure upstream remote.
        """

        def run_side_effect(args, cwd, check, capture_output=False, text=True):
            if args[:3] == ["git", "remote", "-v"]:
                # Pretend we already have no 'upstream' to force add
                return make_cp(stdout="")
            return make_cp()

        mock_run.side_effect = run_side_effect

        # Path.exists should return True when asked about /tmp/temp_repo/.git
        def exists_side_effect(self):
            return str(self).endswith("/tmp/temp_repo/.git")

        with patch("pathlib.Path.exists", new=exists_side_effect):
            self.gha.clone_sync_repository()

        mock_run.assert_any_call(
            ["git", "fetch", "--all", "--prune"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )
        mock_run.assert_any_call(
            ["git", "remote", "-v"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
            [
                "git",
                "remote",
                "add",
                "upstream",
                f"https://github.com/{self.repo_owner}/{self.repo_name}.git",
            ],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )

    @patch("subprocess.run")
    def test_sync_fork_with_upstream_merge_strategy(self, mock_run):
        """
        Ensure sequence: fetch upstream+origin, checkout/ensure base branch, merge, push.
        """

        def run_side_effect(args, cwd, check, capture_output=False, text=True):
            # 'git branch' to check if base exists locally → return no branches, so it creates
            if args[:2] == ["git", "branch"]:
                return make_cp(stdout="")
            if args[:3] == ["git", "remote", "-v"]:
                return make_cp(
                    stdout="upstream\t{url} (fetch)\n".format(
                        url=f"https://github.com/{self.repo_owner}/{self.repo_name}.git"
                    )
                )
            return make_cp()

        mock_run.side_effect = run_side_effect

        # Pretend .git exists so we operate in repo
        def exists_side_effect(self):
            return str(self).endswith("/tmp/temp_repo/.git")

        with patch("pathlib.Path.exists", new=exists_side_effect):
            self.gha.sync_fork_with_upstream(base_branch="main", strategy="merge")

        # Key steps
        mock_run.assert_any_call(
            ["git", "fetch", "upstream", "main"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )
        mock_run.assert_any_call(
            ["git", "fetch", "origin", "main"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )
        # It may try to create local branch from origin first, then upstream
        # We just ensure a merge with upstream and push occurred
        mock_run.assert_any_call(
            ["git", "merge", "upstream/main"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )
        mock_run.assert_any_call(
            ["git", "push", "origin", "main"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        mock_run.return_value = make_cp()
        # Ensure .git exists
        with patch(
            "pathlib.Path.exists",
            new=lambda self: str(self).endswith("/tmp/temp_repo/.git"),
        ):
            self.gha.create_branch("feature/x", from_branch="main")

        mock_run.assert_has_calls(
            [
                call(
                    ["git", "checkout", "main"],
                    cwd="/tmp/temp_repo",
                    check=True,
                    capture_output=False,
                    text=True,
                ),
                call(
                    ["git", "checkout", "-B", "feature/x"],
                    cwd="/tmp/temp_repo",
                    check=True,
                    capture_output=False,
                    text=True,
                ),
            ],
            any_order=False,
        )

    @patch("subprocess.run")
    def test_add_file(self, mock_run):
        mock_run.return_value = make_cp()
        with patch.object(Path, "mkdir") as _mk, patch.object(
            Path, "write_text"
        ) as _wt:
            # Ensure .git exists
            with patch(
                "pathlib.Path.exists",
                new=lambda self: str(self).endswith("/tmp/temp_repo/.git"),
            ):
                self.gha.add_file("dir/file.json", {"k": "v"})

        _wt.assert_called_once()  # JSON written
        mock_run.assert_any_call(
            ["git", "add", "/tmp/temp_repo/dir/file.json"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )

    @patch("subprocess.run")
    def test_commit_and_push(self, mock_run):
        mock_run.return_value = make_cp()
        with patch(
            "pathlib.Path.exists",
            new=lambda self: str(self).endswith("/tmp/temp_repo/.git"),
        ):
            self.gha.commit_and_push("feat", "my message")

        mock_run.assert_has_calls(
            [
                call(
                    ["git", "checkout", "feat"],
                    cwd="/tmp/temp_repo",
                    check=True,
                    capture_output=False,
                    text=True,
                ),
                call(
                    ["git", "commit", "-m", "my message"],
                    cwd="/tmp/temp_repo",
                    check=True,
                    capture_output=False,
                    text=True,
                ),
                call(
                    ["git", "push", "-u", "origin", "feat"],
                    cwd="/tmp/temp_repo",
                    check=True,
                    capture_output=False,
                    text=True,
                ),
            ],
            any_order=False,
        )

    @patch("subprocess.run")
    def test_commit_and_push_nothing_to_commit(self, mock_run):
        # Make the commit call raise like 'git' does when nothing to commit
        def run_side_effect(args, cwd, check, capture_output=False, text=True):
            if args[:2] == ["git", "commit"]:
                e = Exception("nothing to commit, working tree clean")
                # Mimic our _run raising RuntimeError
                raise RuntimeError(str(e))
            return make_cp()

        mock_run.side_effect = run_side_effect

        with patch(
            "pathlib.Path.exists",
            new=lambda self: str(self).endswith("/tmp/temp_repo/.git"),
        ):
            # Should not raise; should still push
            self.gha.commit_and_push("feat", "msg")

        mock_run.assert_any_call(
            ["git", "push", "-u", "origin", "feat"],
            cwd="/tmp/temp_repo",
            check=True,
            capture_output=False,
            text=True,
        )

    @patch("requests.post")
    def test_create_pull_request(self, mock_post):
        mock_post.return_value = MagicMock(
            **{
                "raise_for_status.return_value": None,
                "json.return_value": {"html_url": "https://github.com/test/pull/1"},
            }
        )
        url = self.gha.create_pull_request(
            "feat", "PR title", "Body", base_branch="main"
        )

        self.assertEqual(url, "https://github.com/test/pull/1")
        mock_post.assert_called_once_with(
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls",
            headers={"Authorization": f"token {self.token}"},
            json={
                "title": "PR title",
                "head": f"{self.username}:feat",
                "base": "main",
                "body": "Body",
            },
            timeout=60,
        )

    @patch("shutil.rmtree")
    def test_clean_up(self, mock_rm):
        # Simulate repo path exists
        with patch("pathlib.Path.exists", return_value=True):
            self.gha.clean_up()
        mock_rm.assert_called_once_with(Path("/tmp/temp_repo"))

    def test_file_exists_true(self):
        with patch("pathlib.Path.is_file", return_value=True):
            self.assertTrue(self.gha.file_exists("a/b.json"))

    def test_file_exists_false(self):
        with patch("pathlib.Path.is_file", return_value=False):
            self.assertFalse(self.gha.file_exists("a/b.json"))
