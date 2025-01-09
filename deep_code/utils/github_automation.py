#!/usr/bin/env python3

# Copyright (c) 2024 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import json
import logging
import os
import requests
import subprocess
from pathlib import Path


class GitHubAutomation:
    """Automates GitHub operations needed to create a Pull Request.

        Args:
            username: GitHub username.
            token: Personal access token for GitHub.
            repo_owner: Owner of the repository to fork.
            repo_name: Name of the repository to fork.
        """
    def __init__(self, username: str, token: str, repo_owner: str, repo_name: str):
        self.username = username
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        self.fork_repo_url = (
            f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
        )
        self.local_clone_dir = os.path.join(os.path.expanduser("~"), "temp_repo")

    def fork_repository(self):
        """Fork the repository to the user's GitHub account."""
        logging.info("Forking repository...")
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/forks"
        headers = {"Authorization": f"token {self.token}"}
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        logging.info(f"Repository forked to {self.username}/{self.repo_name}")

    def clone_repository(self):
        """Clone the forked repository locally."""
        logging.info("Cloning forked repository...")
        try:
            subprocess.run(
                ["git", "clone", self.fork_repo_url, self.local_clone_dir], check=True
            )
            os.chdir(self.local_clone_dir)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    @staticmethod
    def create_branch(branch_name: str):
        """Create a new branch in the local repository."""
        logging.info(f"Creating new branch: {branch_name}...")
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed Creating branch: '{branch_name}': {e}")

    def add_file(self, file_path: str, content):
        """Add a new file to the local repository."""
        logging.info(f"Adding new file: {file_path}...")
        full_path = Path(self.local_clone_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            # Convert content to dictionary if it's a PySTAC object
            if hasattr(content, "to_dict"):
                content = content.to_dict()
            f.write(json.dumps(content, indent=2))
        try:
            subprocess.run(["git", "add", str(full_path)], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to add file '{file_path}': {e}")

    @staticmethod
    def commit_and_push(branch_name: str, commit_message: str):
        """Commit changes and push to the forked repository."""
        logging.info("Committing and pushing changes...")
        try:
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to commit and push: {e}")

    def create_pull_request(
        self, branch_name: str, pr_title: str, pr_body: str, base_branch: str = "main"
    ):
        """Create a pull request from the forked repository to the base repository."""
        logging.info("Creating a pull request...")
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/pulls"
        headers = {"Authorization": f"token {self.token}"}
        data = {
            "title": pr_title,
            "head": f"{self.username}:{branch_name}",
            "base": base_branch,
            "body": pr_body,
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        pr_url = response.json()["html_url"]
        logging.info(f"Pull request created: {pr_url}")

    def clean_up(self):
        """Clean up the local cloned repository."""
        logging.info("Cleaning up local repository...")
        os.chdir("..")
        try:
            subprocess.run(["rm", "-rf", self.local_clone_dir])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clean-up local repository: {e}")
