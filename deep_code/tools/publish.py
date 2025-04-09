#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import copy
import json
import logging
from datetime import datetime
from pathlib import Path

import fsspec
import yaml
from pystac import Catalog, Link

from deep_code.constants import (
    EXPERIMENT_BASE_CATALOG_SELF_HREF,
    OSC_BRANCH_NAME,
    OSC_REPO_NAME,
    OSC_REPO_OWNER,
    WORKFLOW_BASE_CATALOG_SELF_HREF,
)
from deep_code.utils.dataset_stac_generator import OscDatasetStacGenerator
from deep_code.utils.github_automation import GitHubAutomation
from deep_code.utils.helper import serialize
from deep_code.utils.ogc_api_record import (
    ExperimentAsOgcRecord,
    LinksBuilder,
    WorkflowAsOgcRecord,
)
from deep_code.utils.ogc_record_generator import OSCWorkflowOGCApiRecordGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GitHubPublisher:
    """
    Base class providing:
      - Reading .gitaccess for credentials
      - Common GitHub automation steps (fork, clone, branch, file commit, pull request)
    """

    def __init__(self, repo_name: str = OSC_REPO_NAME):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}
        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")
        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, repo_name
        )
        self.github_automation.fork_repository()
        self.github_automation.clone_sync_repository()

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


class Publisher:
    """Publishes products (datasets) to the OSC GitHub repository.
    """

    def __init__(
        self,
        dataset_config_path: str,
        workflow_config_path: str,
        environment: str = "production",
    ):
        self.environment = environment
        # Determine repo name based on environment
        repo_name = "open-science-catalog-metadata"

        if environment == "staging":
            repo_name = "open-science-catalog-metadata-staging"
        elif environment == "testing":
            repo_name = "open-science-catalog-metadata-testing"

        # Composition
        self.gh_publisher = GitHubPublisher(repo_name=repo_name)
        self.collection_id = ""
        self.workflow_title = ""

        # Paths to configuration files
        self.dataset_config_path = dataset_config_path
        self.workflow_config_path = workflow_config_path

        # Load configuration files
        self._read_config_files()
        self.collection_id = self.dataset_config.get("collection_id")
        self.workflow_title = self.workflow_config.get("properties", {}).get("title")

        if not self.collection_id:
            raise ValueError("collection_id is missing in dataset config.")

    def _read_config_files(self) -> None:
        with fsspec.open(self.dataset_config_path, "r") as file:
            self.dataset_config = yaml.safe_load(file) or {}
        with fsspec.open(self.workflow_config_path, "r") as file:
            self.workflow_config = yaml.safe_load(file) or {}

    @staticmethod
    def _write_to_file(file_path: str, data: dict):
        """Write a dictionary to a JSON file.

        Args:
            file_path (str): The path to the file.
            data (dict): The data to write.
        """
        # Create the directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            json_content = json.dumps(data, indent=2, default=serialize)
        except TypeError as e:
            raise RuntimeError(f"JSON serialization failed: {e}")

        with open(file_path, "w") as f:
            f.write(json_content)

    def _update_and_add_to_file_dict(
        self, file_dict, catalog_path, update_method, *args
    ):
        """Update a catalog using the specified method and add it to file_dict.

        Args:
            file_dict: The dictionary to which the updated catalog will be added.
            catalog_path: The path to the catalog file.
            update_method: The method to call for updating the catalog.
            *args: Additional arguments to pass to the update method.
        """
        full_path = (
            Path(self.gh_publisher.github_automation.local_clone_dir) / catalog_path
        )
        updated_catalog = update_method(full_path, *args)
        file_dict[full_path] = updated_catalog.to_dict()

    def _update_variable_catalogs(self, generator, file_dict, variable_ids):
        """Update or create variable catalogs and add them to file_dict.

        Args:
            generator: The generator object.
            file_dict: The dictionary to which the updated catalogs will be added.
            variable_ids: A list of variable IDs.
        """
        for var_id in variable_ids:
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

    def publish_dataset(self, write_to_file: bool = False):
        """Prepare dataset/product collection for publishing to the specified GitHub
        repository."""

        dataset_id = self.dataset_config.get("dataset_id")
        self.collection_id = self.dataset_config.get("collection_id")
        documentation_link = self.dataset_config.get("documentation_link")
        access_link = self.dataset_config.get("access_link")
        dataset_status = self.dataset_config.get("dataset_status")
        osc_region = self.dataset_config.get("osc_region")
        osc_themes = self.dataset_config.get("osc_themes")
        cf_params = self.dataset_config.get("cf_parameter")

        if not dataset_id or not self.collection_id:
            raise ValueError("Dataset ID or Collection ID missing in the config.")

        logger.info("Generating STAC collection...")

        generator = OscDatasetStacGenerator(
            dataset_id=dataset_id,
            collection_id=self.collection_id,
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
        product_path = f"products/{self.collection_id}/collection.json"
        file_dict[product_path] = ds_collection.to_dict()

        # Update or create variable catalogs for each osc:variable
        self._update_variable_catalogs(generator, file_dict, variable_ids)

        # Update variable base catalog
        variable_base_catalog_path = "variables/catalog.json"
        self._update_and_add_to_file_dict(
            file_dict,
            variable_base_catalog_path,
            generator.update_variable_base_catalog,
            variable_ids,
        )

        # Update product base catalog
        product_catalog_path = "products/catalog.json"
        self._update_and_add_to_file_dict(
            file_dict, product_catalog_path, generator.update_product_base_catalog
        )

        # Update DeepESDL collection
        deepesdl_collection_path = "projects/deep-earth-system-data-lab/collection.json"
        self._update_and_add_to_file_dict(
            file_dict, deepesdl_collection_path, generator.update_deepesdl_collection
        )

        # Write to files if testing
        if write_to_file:
            for file_path, data in file_dict.items():
                self._write_to_file(file_path, data)  # Pass file_path and data
            return {}
        return file_dict

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        return name.replace(" ", "-").lower() if name else None

    def _update_base_catalog(
        self, catalog_path: str, item_id: str, self_href: str
    ) -> Catalog:
        """Update a base catalog by adding a link to a new item.

        Args:
            catalog_path: Path to the base catalog JSON file.
            item_id: ID of the new item (experiment or workflow).
            self_href: Self-href for the base catalog.

        Returns:
            Updated Catalog object.
        """
        # Load the base catalog
        base_catalog = Catalog.from_file(
            Path(self.gh_publisher.github_automation.local_clone_dir) / catalog_path
        )

        # Add a link to the new item
        base_catalog.add_link(
            Link(
                rel="item",
                target=f"./{item_id}/record.json",
                media_type="application/json",
                title=f"{self.workflow_title}",
            )
        )

        # Set the self-href for the base catalog
        base_catalog.set_self_href(self_href)

        return base_catalog

    def publish_workflow_experiment(self, write_to_file: bool = False):
        """prepare workflow and experiment as ogc api record to publish it to the
        specified GitHub repository."""
        workflow_id = self._normalize_name(self.workflow_config.get("workflow_id"))
        if not workflow_id:
            raise ValueError("workflow_id is missing in workflow config.")

        properties_list = self.workflow_config.get("properties", {})
        osc_themes = properties_list.get("themes")
        contacts = self.workflow_config.get("contact", [])
        links = self.workflow_config.get("links", [])
        jupyter_notebook_url = self.workflow_config.get("jupyter_notebook_url")

        logger.info("Generating OGC API Record for the workflow...")
        rg = OSCWorkflowOGCApiRecordGenerator()
        wf_record_properties = rg.build_record_properties(properties_list, contacts)
        # make a copy for experiment record
        exp_record_properties = copy.deepcopy(wf_record_properties)

        link_builder = LinksBuilder(osc_themes)
        theme_links = link_builder.build_theme_links_for_records()

        workflow_record = WorkflowAsOgcRecord(
            id=workflow_id,
            type="Feature",
            title=self.workflow_title,
            properties=wf_record_properties,
            links=links + theme_links,
            jupyter_notebook_url=jupyter_notebook_url,
            themes=osc_themes,
        )
        # Convert to dictionary and cleanup
        workflow_dict = workflow_record.to_dict()
        if "jupyter_notebook_url" in workflow_dict:
            del workflow_dict["jupyter_notebook_url"]
        if "osc_workflow" in workflow_dict["properties"]:
            del workflow_dict["properties"]["osc_workflow"]
        wf_file_path = f"workflows/{workflow_id}/record.json"
        file_dict = {wf_file_path: workflow_dict}

        # Build properties for the experiment record
        exp_record_properties.type = "experiment"
        exp_record_properties.osc_workflow = workflow_id

        experiment_record = ExperimentAsOgcRecord(
            id=workflow_id,
            title=self.workflow_title,
            type="Feature",
            jupyter_notebook_url=jupyter_notebook_url,
            collection_id=self.collection_id,
            properties=exp_record_properties,
            links=links + theme_links,
        )
        # Convert to dictionary and cleanup
        experiment_dict = experiment_record.to_dict()
        if "jupyter_notebook_url" in experiment_dict:
            del experiment_dict["jupyter_notebook_url"]
        if "collection_id" in experiment_dict:
            del experiment_dict["collection_id"]
        if "osc:project" in experiment_dict["properties"]:
            del experiment_dict["properties"]["osc:project"]
        exp_file_path = f"experiments/{workflow_id}/record.json"
        file_dict[exp_file_path] = experiment_dict

        # Update base catalogs of experiments and workflows with links
        file_dict["experiments/catalog.json"] = self._update_base_catalog(
            catalog_path="experiments/catalog.json",
            item_id=workflow_id,
            self_href=EXPERIMENT_BASE_CATALOG_SELF_HREF,
        )

        file_dict["workflows/catalog.json"] = self._update_base_catalog(
            catalog_path="workflows/catalog.json",
            item_id=workflow_id,
            self_href=WORKFLOW_BASE_CATALOG_SELF_HREF,
        )
        # Write to files if testing
        if write_to_file:
            for file_path, data in file_dict.items():
                self._write_to_file(file_path, data)
            return {}
        return file_dict

    def publish_all(self, write_to_file: bool = False):
        """Publish both dataset and workflow/experiment in a single PR."""
        # Get file dictionaries from both methods
        dataset_files = self.publish_dataset(write_to_file=write_to_file)
        workflow_files = self.publish_workflow_experiment(write_to_file=write_to_file)

        # Combine the file dictionaries
        combined_files = {**dataset_files, **workflow_files}

        if not write_to_file:
            # Create branch name, commit message, PR info
            branch_name = (
                f"{OSC_BRANCH_NAME}-{self.collection_id}"
                f"-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            )
            commit_message = (
                f"Add new dataset collection: {self.collection_id} and "
                f"workflow/experiment: {self.workflow_config.get('workflow_id')}"
            )
            pr_title = (
                f"Add new dataset collection: {self.collection_id} and "
                f"workflow/experiment: {self.workflow_config.get('workflow_id')}"
            )
            pr_body = (
                f"This PR adds a new dataset collection: {self.collection_id} and "
                f"its corresponding workflow/experiment to the repository."
            )

            # Publish all files in one go
            pr_url = self.gh_publisher.publish_files(
                branch_name=branch_name,
                file_dict=combined_files,
                commit_message=commit_message,
                pr_title=pr_title,
                pr_body=pr_body,
            )

            logger.info(f"Pull request created: {pr_url}")
