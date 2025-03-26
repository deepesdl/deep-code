#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

"""Logic for initializing repositories
 Initialize a GitHub repository with the proposed configurations files, an initial
 workflow notebook template (e.g. workflow.ipynb), a template Python package (code and
pyproject.toml), and a template setup for documentation (e.g., using mkdocs),
setup of the build pipeline"""

import subprocess
from pathlib import Path
import logging

import requests

from deep_code.utils.helper import read_git_access_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RepositoryInitializer:
    """
    A utility class to initialize a GitHub repository with configuration files,
    a workflow notebook template, and a Python package template for DeepESDL experiment
    """

    def __init__(self, repo_name: str):
        """
        Initialize the RepositoryInitializer.
        """
        self.repo_name = repo_name
        self.repo_dir = Path(repo_name).absolute()
        self.templates_dir = Path(__file__).parent / "templates"
        git_config = read_git_access_file()
        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")
        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

    def create_local_repo(self) -> None:
        """Create a local directory for the repository and initialize it as a Git repository."""
        logger.info(f"Creating local repository: {self.repo_dir}")
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True)

    def _load_template(self, template_name: str) -> str:
        """Load a template file from the templates directory."""
        template_path = self.templates_dir / template_name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        with open(template_path, "r") as file:
            return file.read()

    def create_config_files(self) -> None:
        """Create configuration files in the repository."""
        logger.info("Creating configuration files...")

        # Create README.md
        readme_content = (f"# {self.repo_name}\n\nThis repository contains workflows "
                          f"and Python code for a DeepESDL Experiment.")
        (self.repo_dir / "README.md").write_text(readme_content)

        # Create .gitignore
        gitignore_content = self._load_template(".gitignore")
        (self.repo_dir / ".gitignore").write_text(gitignore_content)

    def create_jupyter_notebook_template(self) -> None:
        """Create a workflow notebook template (workflow.ipynb)."""
        logger.info("Creating workflow notebook template...")
        workflow_content = self._load_template("workflow.ipynb")
        (self.repo_dir / "workflow.ipynb").write_text(workflow_content)

    def create_python_package(self) -> None:
        """Create a Python package template with a pyproject.toml file."""
        logger.info("Creating Python package template...")

        # Create package directory
        package_dir = self.repo_dir / self.repo_name
        package_dir.mkdir(exist_ok=True)

        # Create __init__.py
        (package_dir / "__init__.py").write_text("# Package initialization\n")

        # Create pyproject.toml
        pyproject_content = self._load_template("pyproject.toml")
        pyproject_content = pyproject_content.replace("{repo_name}", self.repo_name)
        (self.repo_dir / "pyproject.toml").write_text(pyproject_content)

    def create_github_repo(self) -> None:
        """Create a remote GitHub repository and push the local repository."""
        if not self.github_username or not self.github_token:
            logger.warning("GitHub credentials not provided. Skipping remote repository creation.")
            return

        logger.info("Creating remote GitHub repository...")

        repo_url = "https://api.github.com/user/repos"
        repo_data = {
            "name": self.repo_name,
            "description": "Repository for DeepESDL workflows and Python code.",
            "private": True,
        }
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.post(repo_url, json=repo_data, headers=headers)
        response.raise_for_status()

        remote_url = f"https://github.com/{self.github_username}/{self.repo_name}.git"
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=self.repo_dir, check=True)

        logger.info(f"Remote repository created: {remote_url}")

    def create_github_actions_workflow(self) -> None:
        """Create a GitHub Actions workflow for running unit tests."""
        logger.info("Creating GitHub Actions workflow...")

        workflows_dir = self.repo_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = self._load_template("unit-tests.yml")
        (workflows_dir / "unit-tests.yml").write_text(workflow_content)

    def initialize(self) -> None:
        """Initialize the repository with all templates and configurations."""
        self.create_local_repo()
        self.create_config_files()
        self.create_jupyter_notebook_template()
        self.create_python_package()
        self.create_github_repo()
        logger.info(f"Repository '{self.repo_name}' initialized successfully!")


if __name__ == '__main__':
    r = RepositoryInitializer("deepesdl-test-experiment")
    r.initialize()