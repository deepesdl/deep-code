#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import logging
from pathlib import Path
from datetime import datetime

import fsspec
import yaml

from deep_code.constants import (
    OSC_BRANCH_NAME,
    OSC_REPO_NAME,
    OSC_REPO_OWNER,
    WF_BRANCH_NAME,
)
from deep_code.utils.dataset_stac_generator import OscDatasetStacGenerator
from deep_code.utils.github_automation import GitHubAutomation
from deep_code.utils.ogc_api_record import OgcRecord
from deep_code.utils.ogc_record_generator import OSCWorkflowOGCApiRecordGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GitHubPublisher:
    """
    Base class providing:
      - Reading .gitaccess for credentials
      - Common GitHub automation steps (fork, clone, branch, file commit, pull request)
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
        self.github_automation.fork_repository()
        self.github_automation.clone_repository()

    def publish_files(
        self,
        branch_name: str,
        file_dict: dict[str, dict],
        commit_message: str,
        pr_title: str,
        pr_body: str,
    ) -> str:
        """Publish multiple files to a new branch and open a PR.

        Args:
            branch_name: Branch name to create (e.g. "osc-branch-collectionid").
            file_dict: { file_path: file_content_dict } for each file to commit.
            commit_message: Commit message for all changes.
            pr_title: Title of the pull request.
            pr_body: Description/body of the pull request.

        Returns:
            URL of the created pull request.
        """
        try:
            self.github_automation.create_branch(branch_name)

            # Add each file to the branch
            for file_path, content in file_dict.items():
                logger.info(f"Adding {file_path} to {branch_name}")
                self.github_automation.add_file(file_path, content)

            # Commit and push
            self.github_automation.commit_and_push(branch_name, commit_message)

            # Create pull request
            pr_url = self.github_automation.create_pull_request(
                branch_name, pr_title, pr_body
            )
            logger.info(f"Pull request created: {pr_url}")
            return pr_url

        finally:
            # Cleanup local clone
            self.github_automation.clean_up()


class DatasetPublisher:
    """Publishes products (datasets) to the OSC GitHub repository.
    Inherits from BasePublisher for GitHub publishing logic.
    """

    def __init__(self):
        # Composition
        self.gh_publisher = GitHubPublisher()

    def publish_dataset(self, dataset_config_path: str):
        """Publish a product collection to the specified GitHub repository."""
        with fsspec.open(dataset_config_path, "r") as file:
            dataset_config = yaml.safe_load(file) or {}

        dataset_id = dataset_config.get("dataset_id")
        collection_id = dataset_config.get("collection_id")
        documentation_link = dataset_config.get("documentation_link")
        access_link = dataset_config.get("access_link")
        dataset_status = dataset_config.get("dataset_status")
        osc_region = dataset_config.get("osc_region")
        osc_themes = dataset_config.get("osc_themes")
        cf_params = dataset_config.get("cf_parameter")

        if not dataset_id or not collection_id:
            raise ValueError("Dataset ID or Collection ID missing in the config.")

        logger.info("Generating STAC collection...")

        generator = OscDatasetStacGenerator(
            dataset_id=dataset_id,
            collection_id=collection_id,
            documentation_link=documentation_link,
            access_link=access_link,
            osc_status=dataset_status,
            osc_region=osc_region,
            osc_themes=osc_themes,
            cf_params=cf_params,
        )

        variable_ids = generator.get_variable_ids()
        ds_collection = generator.build_dataset_stac_collection()

        # Prepare a dictionary of file paths and content
        file_dict = {}
        product_path = f"products/{collection_id}/collection.json"
        file_dict[product_path] = ds_collection.to_dict()

        variable_base_catalog_path = f"variables/catalog.json"
        variable_catalog_full_path = (
                Path(self.gh_publisher.github_automation.local_clone_dir)
                / variable_base_catalog_path
        )
        # Add or update variable files
        for var_id in variable_ids:
            # if var_id in ["crs", "spatial_ref"]:
            #     logger.info(f"Skipping CRS variable: {var_id}")
            #     continue
            var_file_path = f"variables/{var_id}/catalog.json"
            if not self.gh_publisher.github_automation.file_exists(var_file_path):
                logger.info(
                    f"Variable catalog for {var_id} does not exist. Creating..."
                )
                var_metadata = generator.variables_metadata.get(var_id)
                var_catalog = generator.build_variable_catalog(var_metadata)
                file_dict[var_file_path] = var_catalog.to_dict()
            else:
                logger.info(
                    f"Variable catalog already exists for {var_id}, adding product link."
                )
                full_path = (
                    Path(self.gh_publisher.github_automation.local_clone_dir)
                    / var_file_path
                )
                updated_catalog = generator.update_existing_variable_catalog(
                    full_path, var_id
                )
                file_dict[var_file_path] = updated_catalog.to_dict()
                # logger.info(
                #     f"Add {var_id} child link to variable base catalog"
                # )
                # file_dict[
                #     variable_base_catalog_path] = generator.update_variable_base_catalog(
                #     variable_catalog_full_path, var_id).to_dict()


        file_dict[variable_base_catalog_path] = generator.update_variable_base_catalog(
            variable_catalog_full_path, variable_ids
        ).to_dict()
        """Link product to base product catalog"""
        product_catalog_path = f"products/catalog.json"
        full_path = (
                Path(self.gh_publisher.github_automation.local_clone_dir)
                / product_catalog_path
        )
        updated_product_base_catalog = generator.update_product_base_catalog(full_path)
        file_dict[product_catalog_path] = updated_product_base_catalog.to_dict()

        #Link product to project catalog
        deepesdl_collection_path = \
            f"projects/deep-earth-system-data-lab/collection.json"
        deepesdl_collection_full_path = (
                Path(self.gh_publisher.github_automation.local_clone_dir)
                / deepesdl_collection_path
        )
        updated_deepesdl_collection = generator.update_deepesdl_collection(deepesdl_collection_full_path)
        file_dict[deepesdl_collection_path] = updated_deepesdl_collection.to_dict()

        # Create branch name, commit message, PR info
        branch_name = f"{OSC_BRANCH_NAME}-{collection_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        commit_message = f"Add new dataset collection: {collection_id}"
        pr_title = f"Add new dataset collection: {collection_id}"
        pr_body = (f"This PR adds a new dataset collection: {collection_id} and it's "
                   f"corresponding variable catalogs to the repository.")

        # Publish all files in one go
        pr_url = self.gh_publisher.publish_files(
            branch_name=branch_name,
            file_dict=file_dict,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=pr_body,
        )

        logger.info(f"Pull request created: {pr_url}")


class WorkflowPublisher:
    """Publishes workflows to the OSC GitHub repository."""

    def __init__(self):
        self.gh_publisher = GitHubPublisher()

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        return name.replace(" ", "-").lower() if name else None

    def publish_workflow(self, workflow_config_path: str):
        with fsspec.open(workflow_config_path, "r") as file:
            workflow_config = yaml.safe_load(file) or {}

        workflow_id = self._normalize_name(workflow_config.get("workflow_id"))
        if not workflow_id:
            raise ValueError("workflow_id is missing in workflow config.")

        properties_list = workflow_config.get("properties", [])
        contacts = workflow_config.get("contact", [])
        links = workflow_config.get("links", [])

        logger.info("Generating OGC API Record for the workflow...")
        rg = OSCWorkflowOGCApiRecordGenerator()
        wf_record_properties = rg.build_record_properties(properties_list, contacts)

        ogc_record = OgcRecord(
            id=workflow_id,
            type="Feature",
            time={},
            properties=wf_record_properties,
            links=links,
        )

        file_path = f"workflow/{workflow_id}/collection.json"

        # Prepare the single file dict
        file_dict = {file_path: ogc_record.to_dict()}

        branch_name = f"{WF_BRANCH_NAME}-{workflow_id}"
        commit_message = f"Add new workflow: {workflow_id}"
        pr_title = "Add new workflow"
        pr_body = "This PR adds a new workflow to the OSC repository."

        pr_url = self.gh_publisher.publish_files(
            branch_name=branch_name,
            file_dict=file_dict,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=pr_body,
        )

        logger.info(f"Pull request created: {pr_url}")

