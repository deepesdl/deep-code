#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import requests

from deep_code.utils.helper import serialize


class GitHubAutomation:
    """Automates GitHub operations needed to create a Pull Request.

    Args:
        username: GitHub username.
        token: Personal access token for GitHub.
        repo_owner: Owner of the repository to fork.
        repo_name: Name of the repository to fork.
        local_clone_dir: Optional path to use for local clone (defaults to ~/temp_repo).
    """

    def __init__(
        self,
        username: str,
        token: str,
        repo_owner: str,
        repo_name: str,
        local_clone_dir: str | None = None,
    ):
        self.username = username
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name

        self.base_repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        # Tokenized origin URL for pushes to the fork
        self.origin_repo_url = (
            f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
        )
        self.local_clone_dir = (
            os.path.join(os.path.expanduser("~"), "temp_repo")
            if local_clone_dir is None
            else local_clone_dir
        )

    def _run(
        self,
        cmd: list[str],
        cwd: str | Path | None = None,
        check: bool = True,
        capture_output: bool = False,
        text: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a subprocess command with consistent logging and error handling."""
        cwd_str = str(cwd) if cwd is not None else str(self.local_clone_dir)
        logging.debug("RUN: %s (cwd=%s)", " ".join(cmd), cwd_str)
        try:
            return subprocess.run(
                cmd, cwd=cwd_str, check=check, capture_output=capture_output, text=text
            )
        except subprocess.CalledProcessError as e:
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            ) from e

    def _run_git(self, args: list[str], cwd: str | Path | None = None) -> None:
        self._run(["git", *args], cwd=cwd)

    def _git_output(self, args: list[str]) -> str:
        res = self._run(["git", *args], capture_output=True)
        return res.stdout

    def _ensure_repo_dir(self) -> Path:
        path = Path(self.local_clone_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_upstream_remote(self) -> None:
        """Ensure a remote named 'upstream' points to the base repo."""
        repo = self._ensure_repo_dir()
        remotes = self._git_output(["remote", "-v"])
        upstream_url = self.base_repo_url

        if "upstream" not in remotes:
            logging.info("Adding 'upstream' remote -> %s", upstream_url)
            self._run_git(["remote", "add", "upstream", upstream_url], cwd=repo)
        else:
            # If the URL mismatches, fix it
            if f"upstream\t{upstream_url} (fetch)" not in remotes:
                logging.info("Updating 'upstream' remote URL -> %s", upstream_url)
                self._run_git(["remote", "set-url", "upstream", upstream_url], cwd=repo)

    def fork_repository(self) -> None:
        """Fork the repository to the user's GitHub account."""
        logging.info("Forking repository...")
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/forks"
        headers = {"Authorization": f"token {self.token}"}
        response = requests.post(url, headers=headers, timeout=60)
        response.raise_for_status()
        logging.info("Repository forked to %s/%s", self.username, self.repo_name)

    def clone_sync_repository(self) -> None:
        """Clone the forked repository locally if missing; otherwise fetch & fast-forward origin."""
        repo = self._ensure_repo_dir()
        git_dir = repo / ".git"

        if not git_dir.exists():
            logging.info("Cloning fork: %s -> %s", self.origin_repo_url, repo)
            self._run(["git", "clone", self.origin_repo_url, str(repo)], cwd=".")
            # Ensure default branch is tracked locally (we don't assume 'main')
            # This will be handled by later sync step.
        else:
            logging.info("Local clone exists; fetching latest from origin.")
            self._run_git(["fetch", "--all", "--prune"], cwd=repo)

        # Always ensure we have the upstream remote configured
        self._ensure_upstream_remote()

    def sync_fork_with_upstream(
        self, base_branch: str = "main", strategy: str = "merge"
    ) -> None:
        """Sync local and origin base branch from upstream base branch.
        strategy:
          - 'ff'     : fast-forward only
          - 'rebase' : rebase local base_branch onto upstream/base_branch
          - 'merge'  : merge upstream/base_branch into local/base_branch (default)
        """
        repo = self._ensure_repo_dir()
        logging.info(
            "Syncing fork with upstream (%s) on branch '%s'...", strategy, base_branch
        )

        # Make sure remotes are present and fresh
        self._ensure_upstream_remote()
        self._run_git(["fetch", "upstream", base_branch], cwd=repo)
        self._run_git(["fetch", "origin", base_branch], cwd=repo)

        # Ensure we have a local branch for base_branch
        local_branches = self._git_output(["branch"])
        if f" {base_branch}\n" not in (local_branches + "\n"):
            # Create local base branch tracking origin/base_branch if it exists, otherwise upstream
            try:
                self._run_git(
                    ["checkout", "-b", base_branch, f"origin/{base_branch}"], cwd=repo
                )
            except RuntimeError:
                self._run_git(
                    ["checkout", "-b", base_branch, f"upstream/{base_branch}"], cwd=repo
                )
        else:
            self._run_git(["checkout", base_branch], cwd=repo)

        if strategy == "ff":
            self._run_git(["merge", "--ff-only", f"upstream/{base_branch}"], cwd=repo)
        elif strategy == "rebase":
            self._run_git(["rebase", f"upstream/{base_branch}"], cwd=repo)
        elif strategy == "merge":
            self._run_git(["merge", f"upstream/{base_branch}"], cwd=repo)
        else:
            raise ValueError("strategy must be one of: 'ff', 'rebase', 'merge'")

        # Push updated base branch to fork
        self._run_git(["push", "origin", base_branch], cwd=repo)
        logging.info(
            "Fork origin/%s is now aligned with upstream/%s.", base_branch, base_branch
        )

    def create_branch(self, branch_name: str, from_branch: str = "main") -> None:
        """Create or reset a local branch from a given base branch."""
        repo = self._ensure_repo_dir()
        logging.info("Creating branch '%s' from '%s'...", branch_name, from_branch)

        # Ensure base exists locally (caller should have synced beforehand)
        self._run_git(["checkout", from_branch], cwd=repo)
        # -B creates or resets the branch to the current HEAD of from_branch
        self._run_git(["checkout", "-B", branch_name], cwd=repo)

    def add_file(self, file_path: str, content: Any) -> None:
        """Add a new file (serialized to JSON) to the local repository and stage it."""
        repo = self._ensure_repo_dir()
        full_path = Path(repo) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize content to something JSON serializable
        if hasattr(content, "to_dict"):
            content = content.to_dict()
        if not isinstance(content, (dict, list, str, int, float, bool, type(None))):
            raise TypeError(f"Cannot serialize content of type {type(content)}")

        try:
            json_content = json.dumps(
                content, indent=2, ensure_ascii=False, default=serialize
            )
        except TypeError as e:
            raise RuntimeError(
                f"JSON serialization failed for '{file_path}': {e}"
            ) from e

        full_path.write_text(json_content, encoding="utf-8")
        self._run_git(["add", str(full_path)], cwd=repo)
        logging.info("Added and staged file: %s", file_path)

    def commit_and_push(self, branch_name: str, commit_message: str) -> None:
        """Commit staged changes on the branch and push to origin."""
        repo = self._ensure_repo_dir()
        logging.info("Committing and pushing changes on '%s'...", branch_name)

        self._run_git(["checkout", branch_name], cwd=repo)
        try:
            self._run_git(["commit", "-m", commit_message], cwd=repo)
        except RuntimeError as e:
            if "nothing to commit" in str(e).lower():
                logging.info("Nothing to commit on '%s'; pushing anyway.", branch_name)
            else:
                raise
        self._run_git(["push", "-u", "origin", branch_name], cwd=repo)

    def create_pull_request(
        self, branch_name: str, pr_title: str, pr_body: str, base_branch: str = "main"
    ) -> str:
        """Create a pull request from fork:branch_name → base_repo:base_branch.

        Returns:
            The created PR URL.
        """
        logging.info(
            "Creating pull request '%s' -> base:%s ...", branch_name, base_branch
        )
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"
        headers = {"Authorization": f"token {self.token}"}
        data = {
            "title": pr_title,
            "head": f"{self.username}:{branch_name}",
            "base": base_branch,
            "body": pr_body,
        }
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        pr_url = response.json().get("html_url", "")
        logging.info("Pull request created: %s", pr_url)
        return pr_url

    def clean_up(self) -> None:
        """Remove the local cloned repository directory."""
        repo = Path(self.local_clone_dir)
        logging.info("Cleaning up local repository at %s ...", repo)
        try:
            if repo.exists():
                shutil.rmtree(repo)
        except Exception as e:
            raise RuntimeError(
                f"Failed to clean up local repository '{repo}': {e}"
            ) from e

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists within the local clone directory."""
        full_path = Path(self.local_clone_dir) / file_path
        exists = full_path.is_file()
        logging.debug("Checking existence of %s: %s", full_path, exists)
        return exists
