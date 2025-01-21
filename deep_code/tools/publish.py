#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import logging
from pathlib import Path

import fsspec
import yaml

from deep_code.constants import (
    OSC_BRANCH_NAME,
    OSC_REPO_NAME,
    OSC_REPO_OWNER,
    WF_BRANCH_NAME,
)
from deep_code.utils.dataset_stac_generator import OSCDatasetSTACGenerator
from deep_code.utils.github_automation import GitHubAutomation
from deep_code.utils.ogc_api_record import OgcRecord
from deep_code.utils.ogc_record_generator import OSCWorkflowOGCApiRecordGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BasePublisher:
    """
    Base class providing common GitHub automation steps:
      - Reading credentials from `.gitaccess`
      - Setting up GitHubAutomation
      - Forking, cloning, creating a branch
      - Adding files, committing, pushing
      - Creating a pull request
    """

    def __init__(self):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}

        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")
        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, OSC_REPO_NAME
        )

    def publish_file(
        self,
        branch_name: str,
        file_path: str,
        file_content: dict,
        commit_message: str,
        pr_title: str,
        pr_body: str,
    ) -> str:
        """
        Publish a single file to GitHub in a new branch and open a PR.

        Args:
            branch_name: Name of the branch to create (e.g. 'osc-branch-collectionid').
            file_path: File path in the repo (e.g. 'products/.../collection.json').
            file_content: The JSON/dict content to commit.
            commit_message: Commit message.
            pr_title: Title for the pull request.
            pr_body: Body of the pull request.

        Returns:
            str: The URL of the created pull request.
        """
        try:
            logger.info("Starting GitHub automation...")
            self.github_automation.fork_repository()
            self.github_automation.clone_repository()
            self.github_automation.create_branch(branch_name)

            # Add the file
            self.github_automation.add_file(file_path, file_content)

            # Commit and push
            self.github_automation.commit_and_push(branch_name, commit_message)

            # Create pull request
            pr_url = self.github_automation.create_pull_request(
                branch_name, pr_title, pr_body
            )
            logger.info(f"Pull request created at: {pr_url}")
            return pr_url

        finally:
            # Always clean up local clone
            self.github_automation.clean_up()


class DatasetPublisher:
    """
    Publishes products to the OSC GitHub repository.

    Credentials must be provided via a hidden file named `.gitaccess`, located in
    the root of the repository. This file is expected to contain YAML of the form:

        github-username: "YOUR_GITHUB_USERNAME"
        github-token: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
    """

    def __init__(self):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}

        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")

        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, OSC_REPO_NAME
        )

    def publish_dataset(self, dataset_config_path: str):
        """Publish a product collection to the specified GitHub repository.

        Args:
             dataset_config_path: Path to the YAML file containing dataset config
        """
        with fsspec.open(dataset_config_path, "r") as file:
            dataset_config = yaml.safe_load(file)

        dataset_id = dataset_config.get("dataset_id")
        collection_id = dataset_config.get("collection_id")
        documentation_link = dataset_config.get("documentation_link")
        access_link = dataset_config.get("access_link")
        dataset_status = dataset_config.get("dataset_status")
        osc_region = dataset_config.get("osc_region")
        osc_themes = dataset_config.get("osc_themes")
        cf_params = dataset_config.get("cf_parameter")

        if not dataset_id or not collection_id:
            raise ValueError(
                "Dataset ID or Collection ID is missing in the dataset-config.yaml "
                "file."
            )

        try:
            logger.info("Generating STAC collection...")
            generator = OSCDatasetSTACGenerator(
                dataset_id=dataset_id,
                collection_id=collection_id,
                documentation_link=documentation_link,
                access_link=access_link,
                osc_status=dataset_status,
                osc_region=osc_region,
                osc_themes=osc_themes,
                cf_params=cf_params,
            )
            # get variables from the datasets
            variable_ids = generator.get_variable_ids()
            # build STAC collection for the dataset
            ds_collection = generator.build_dataset_stac_collection()

            file_path = f"products/{collection_id}/collection.json"
            logger.info("Automating GitHub tasks...")
            self.github_automation.fork_repository()
            self.github_automation.clone_repository()
            OSC_NEW_BRANCH_NAME = OSC_BRANCH_NAME + "-" + collection_id
            self.github_automation.create_branch(OSC_NEW_BRANCH_NAME)

            for var_id in variable_ids:
                var_file_path = f"variables/{var_id}/catalog.json"
                if not self.github_automation.file_exists(var_file_path):
                    logger.info(
                        f"Variable catalog for {var_id} does not exist. Creating..."
                    )
                    var_metadata = generator.variables_metadata.get(var_id)
                    var_catalog = generator.build_variable_catalog(var_metadata)
                    self.github_automation.add_file(
                        var_file_path, var_catalog.to_dict()
                    )
                else:
                    logger.info(
                        f"Variable catalog already exists for {var_id}. so add the "
                        f"product as child link..."
                    )
                    full_path = (
                        Path(self.github_automation.local_clone_dir) / var_file_path
                    )
                    self.github_automation.add_file(
                        var_file_path,
                        generator.update_existing_variable_catalog(
                            full_path, var_id
                        ).to_dict(),
                    )

            self.github_automation.add_file(file_path, ds_collection.to_dict())

            self.github_automation.commit_and_push(
                OSC_NEW_BRANCH_NAME, f"Add new collection:{collection_id}"
            )
            pr_url = self.github_automation.create_pull_request(
                OSC_NEW_BRANCH_NAME,
                f"Add new dataset collection",
                "This PR adds a new collection to the repository.",
            )

            logger.info(f"Pull request created: {pr_url}")

        finally:
            self.github_automation.clean_up()


class WorkflowPublisher:
    """Publishes workflow to the OSC GitHub repository.

        Credentials must be provided via a hidden file named `.gitaccess`, located in
        the root of the repository. This file is expected to contain YAML of the form:

            github-username: "YOUR_GITHUB_USERNAME"
            github-token: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
        """

    def __init__(self):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}

        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")

        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, OSC_REPO_NAME
        )

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        return name.replace(" ", "-").lower() if name else None

    def publish_workflow(self, workflow_config_path: str):

        with fsspec.open(workflow_config_path, "r") as file:
            workflow_config = yaml.safe_load(file)

        try:
            logger.info("Generating OGC API Record for the workflow...")
            workflow_id = self._normalize_name(workflow_config.get("workflow_id"))
            properties_list = workflow_config.get("properties", [])

            contacts = workflow_config.get("contact", [])
            rg = OSCWorkflowOGCApiRecordGenerator()
            wf_record_properties = rg.build_record_properties(properties_list, contacts)

            links = workflow_config.get("links")
            ogc_record = OgcRecord(
                id=workflow_id,
                type="Feature",
                time={},
                properties=wf_record_properties,
                links=links,
            )

            file_path = f"workflow/{workflow_id}/collection.json"
            logger.info("Automating GitHub tasks...")
            self.github_automation.fork_repository()
            self.github_automation.clone_repository()
            WF_NEW_BRANCH_NAME = WF_BRANCH_NAME + "-" + workflow_id
            self.github_automation.create_branch(WF_NEW_BRANCH_NAME)
            self.github_automation.add_file(file_path, ogc_record.to_dict())
            self.github_automation.commit_and_push(
                WF_NEW_BRANCH_NAME, f"Add new workflow:{workflow_id}"
            )
            pr_url = self.github_automation.create_pull_request(
                WF_NEW_BRANCH_NAME,
                f"Add new collection",
                "This PR adds a new workflow to the OSC repository.",
            )
            logger.info(f"Pull request created: {pr_url}")

        finally:
            self.github_automation.clean_up()
