import logging
import yaml
import fsspec

from deep_code.utils.github_automation import GitHubAutomation
from deep_code.utils.dataset_stac_generator import OSCProductSTACGenerator
from deep_code.constants import OSC_REPO_OWNER, OSC_REPO_NAME, OSC_NEW_BRANCH_NAME

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class ProductPublisher:
    def __init__(self, git_config_path: str):
        """
        Initialize the ProductPublisher class.
        :param git_config_path: Path to the YAML file containing GitHub credentials
        """
        with fsspec.open(git_config_path, "r") as file:
            git_config = yaml.safe_load(file) or {}

        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")

        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the git.yaml file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, OSC_REPO_NAME
        )

    def publish_product(
        self,
        dataset_config_path: str,
    ):
        """
        Publish a product collection to the specified GitHub repository.

        :param dataset_config_path: Path to the YAML file containing dataset configuration
        """
        with fsspec.open(dataset_config_path, "r") as file:
            dataset_config = yaml.safe_load(file)

        dataset_id = dataset_config.get("dataset-id")
        collection_id = dataset_config.get("collection-id")
        documentation_link = dataset_config.get("documentation-link")
        access_link = dataset_config.get("access-link")
        dataset_status = dataset_config.get("dataset-status")
        osc_region = dataset_config.get("dataset-region")
        dataset_theme = dataset_config.get("dataset-theme")

        if not dataset_id or not collection_id:
            raise ValueError("Dataset ID or Collection ID is missing in the dataset-config.yaml file.")

        try:
            logger.info("Generating STAC collection...")
            generator = OSCProductSTACGenerator(
                dataset_id=dataset_id,
                collection_id=collection_id,
                documentation_link=documentation_link,
                access_link=access_link,
                osc_status=dataset_status,
                osc_region=osc_region,
                osc_themes=dataset_theme
            )
            collection = generator.build_stac_collection()
            collection.extra_fields["documentation_link"] = documentation_link

            file_path = f"products/{collection_id}/collection.json"
            logger.info("Automating GitHub tasks...")
            self.github_automation.fork_repository()
            self.github_automation.clone_repository()
            self.github_automation.create_branch(OSC_NEW_BRANCH_NAME)
            self.github_automation.add_file(file_path, collection.to_dict())
            self.github_automation.commit_and_push(
                OSC_NEW_BRANCH_NAME, f"Add new collection: {collection_id}"
            )
            pr_url = self.github_automation.create_pull_request(
                OSC_NEW_BRANCH_NAME,
                f"Add new collection",
                "This PR adds a new collection to the repository.",
            )

            logger.info(f"Pull request created: {pr_url}")

        finally:
            self.github_automation.clean_up()



