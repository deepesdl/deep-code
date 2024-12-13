import os
import json
import subprocess
import requests
from pathlib import Path


class GitHubAutomation:
    def __init__(self, username: str, token: str, repo_owner: str, repo_name: str):
        """
        Initialize the GitHubAutomation class.

        :param username: Your GitHub username
        :param token: Your GitHub personal access token
        :param repo_owner: Owner of the repository to fork
        :param repo_name: Name of the repository to fork
        """
        self.username = username
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        self.fork_repo_url = f"https://github.com/{username}/{repo_name}.git"
        self.local_clone_dir = "./temp_repo"

    def fork_repository(self):
        """Fork the repository to the user's GitHub account."""
        print("Forking repository...")
        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/forks"
        headers = {"Authorization": f"token {self.token}"}
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        print(f"Repository forked to {self.username}/{self.repo_name}")

    def clone_repository(self):
        """Clone the forked repository locally."""
        print("Cloning forked repository...")
        subprocess.run(
            ["git", "clone", self.fork_repo_url, self.local_clone_dir], check=True
        )
        os.chdir(self.local_clone_dir)

    def create_branch(self, branch_name: str):
        """Create a new branch in the local repository."""
        print(f"Creating new branch: {branch_name}...")
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

    def add_file(self, file_path: str, content: dict):
        """Add a new file to the local repository."""
        print(f"Adding new file: {file_path}...")
        full_path = Path(self.local_clone_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(json.dumps(content, indent=2))
        subprocess.run(["git", "add", str(full_path)], check=True)

    def commit_and_push(self, branch_name: str, commit_message: str):
        """Commit changes and push to the forked repository."""
        print("Committing and pushing changes...")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)

    def create_pull_request(
        self, branch_name: str, pr_title: str, pr_body: str, base_branch: str = "main"
    ):
        """Create a pull request from the forked repository to the base repository."""
        print("Creating a pull request...")
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
        print(f"Pull request created: {pr_url}")

    def clean_up(self):
        """Clean up the local cloned repository."""
        print("Cleaning up local repository...")
        os.chdir("..")
        subprocess.run(["rm", "-rf", self.local_clone_dir])


# if __name__ == "__main__":
#     # Configuration
#     GITHUB_USERNAME = "your-username"  # Replace with your GitHub username
#     GITHUB_TOKEN = "your-personal-access-token"  # Replace with your GitHub PAT
#     REPO_OWNER = "ESA-EarthCODE"
#     REPO_NAME = "open-science-catalog-metadata-testing"
#     NEW_BRANCH_NAME = "add-new-collection"
#     NEW_FILE_PATH = "products/new-collection-folder/collection.json"
#     COLLECTION_CONTENT = {
#         "id": "example-collection",
#         "description": "An example collection",
#         "items": []
#     }
#
#     try:
#         github_automation = GitHubAutomation(GITHUB_USERNAME, GITHUB_TOKEN, REPO_OWNER, REPO_NAME)
#
#         # Automate the process
#         github_automation.fork_repository()
#         github_automation.clone_repository()
#         github_automation.create_branch(NEW_BRANCH_NAME)
#         github_automation.add_file(NEW_FILE_PATH, COLLECTION_CONTENT)
#         github_automation.commit_and_push(NEW_BRANCH_NAME, "Add new collection")
#         github_automation.create_pull_request(NEW_BRANCH_NAME, "Add new collection", "This PR adds a new collection folder to the products directory.")
#     finally:
#         github_automation.clean_up()
