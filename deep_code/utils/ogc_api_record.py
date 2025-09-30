from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlencode, urlparse

from xrlint.util.constructible import MappingConstructible
from xrlint.util.serializable import JsonSerializable, JsonValue

from deep_code.constants import (
    APPLICATION_STAC_EXTENSION_SPEC,
    APPLICATION_TYPE_JUPYTER_SPEC,
    BASE_URL_OSC,
    DEEPESDL_GIT_PULL_BASE,
    OGC_API_RECORD_SPEC,
    PROJECT_COLLECTION_NAME,
)


class Contact(MappingConstructible["Contact"], JsonSerializable):
    def __init__(
        self,
        name: str | None = None,
        organization: str | None = None,
        position: str | None = None,
        links: list[dict[str, Any]] | None = None,
        contactInstructions: str | None = None,
        roles: list[str] | None = None,
    ):
        self.name = name
        self.organization = organization
        self.position = position
        self.links = links
        self.contactInstructions = contactInstructions
        self.roles = roles

    def to_dict(self, value_name: str | None = None) -> dict[str, JsonValue]:
        """Serialize to JSON, dropping None values."""
        data = {
            "name": self.name,
            "organization": self.organization,
            "position": self.position,
            "links": self.links,
            "contactInstructions": self.contactInstructions,
            "roles": self.roles,
        }
        # keep only explicitly set fields
        return {k: v for k, v in data.items() if v is not None}


class ThemeConcept(MappingConstructible["ThemeConcept"], JsonSerializable):
    def __init__(self, id: str):
        self.id = id


class Theme(MappingConstructible["Theme"], JsonSerializable):
    def __init__(self, concepts: list, scheme: str):
        self.concepts = concepts
        self.scheme = scheme


class JupyterKernelInfo(MappingConstructible["RecordProperties"], JsonSerializable):
    def __init__(self, name: str, python_version: float, env_file: str):
        self.name = name
        self.python_version = python_version
        self.env_file = env_file


class RecordProperties(MappingConstructible["RecordProperties"], JsonSerializable):
    def __init__(
        self,
        created: str,
        type: str,
        title: str,
        description: str,
        jupyter_kernel_info: JupyterKernelInfo,
        osc_project: str,
        osc_workflow: str = None,
        updated: str = None,
        contacts: list[Contact] = None,
        themes: list[Theme] = None,
        keywords: list[str] | None = None,
        formats: list[dict] | None = None,
        license: str = None,
    ):
        self.created = created
        self.updated = updated
        self.type = type
        self.title = title
        self.description = description
        self.jupyter_kernel_info = jupyter_kernel_info
        self.osc_project = osc_project
        self.osc_workflow = osc_workflow
        self.keywords = keywords or []
        self.contacts = contacts
        self.themes = themes
        self.formats = formats or []
        self.license = license

    def to_dict(self, value_name: str | None = None) -> dict[str, JsonValue]:
        """Convert this object into a JSON-serializable dictionary."""
        data = super().to_dict(value_name)
        if self.osc_workflow is not None:
            data["osc:workflow"] = self.osc_workflow
            del data["osc_workflow"]  # Remove the original key as it has been renamed
        if self.osc_project is not None:
            data["osc:project"] = self.osc_project
            del data["osc_project"]
        data["application:type"] = "jupyter-notebook"
        data["application:container"] = ("true",)
        data["application:language"] = ("Python",)
        return data


class LinksBuilder:
    def __init__(self, themes: list[str], jupyter_kernel_info: dict[str]):
        self.themes = themes
        self.jupyter_kernel_info = jupyter_kernel_info
        self.theme_links = []

    def build_theme_links_for_records(self):
        for theme in self.themes:
            formatted_theme = theme.capitalize()
            link = {
                "rel": "related",
                "href": f"../../themes/{theme}/catalog.json",
                "type": "application/json",
                "title": f"Theme: {formatted_theme}",
            }
            self.theme_links.append(link)
        return self.theme_links

    @staticmethod
    def build_link_to_dataset(collection_id) -> list[dict[str, str]]:
        return [
            {
                "rel": "child",
                "href": f"../../products/{collection_id}/collection.json",
                "type": "application/json",
                "title": f"{collection_id}",
            }
        ]

    def build_child_link_to_related_experiment(self) -> list[dict[str, str]]:
        """Build a link to the related experiment record if publishing mode is 'all'."""
        return [
            {
                "rel": "child",
                "href": f"../../experiments/{self.id}/record.json",
                "type": "application/json",
                "title": self.title,
            }
        ]

    def build_link_to_jnb(self, workflow_title, jupyter_nb_url) -> List[Dict[str, Any]]:
        return [
            {
                "rel": "application",
                "title": f"Jupyter Notebook: {workflow_title}",
                "href": jupyter_nb_url,
                "type": "application/x-ipynb+json",
                "application:type": "jupyter-notebook",
                "application:container": "true",
                "application:language": "Python",
                "jupyter:kernel": {
                    "name": self.jupyter_kernel_info["name"],
                    "pythonVersion": self.jupyter_kernel_info["python_version"],
                    "envFile": self.jupyter_kernel_info["env_file"],
                },
            }
        ]

    @staticmethod
    def _parse_github_notebook_url(url: str) -> Tuple[str, str, str, str]:
        """
        Returns (repo_url, repo_name, branch, file_path_in_repo) from a GitHub URL.

        Supports:
          - https://github.com/<owner>/<repo>/blob/<branch>/<path/to/notebook.ipynb>
          - https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path/to/notebook.ipynb>
        """
        p = urlparse(url)
        parts = p.path.strip("/").split("/")

        if p.netloc == "github.com":
            if len(parts) >= 5 and parts[2] in ("blob", "tree"):
                owner, repo, _blob_or_tree, branch = parts[:4]
                file_path = "/".join(parts[4:])
            else:
                raise ValueError(f"Unexpected GitHub URL format: {url}")
            repo_url = f"https://github.com/{owner}/{repo}"
            repo_name = repo

        elif p.netloc == "raw.githubusercontent.com":
            if len(parts) >= 4:
                owner, repo, branch = parts[:3]
                file_path = "/".join(parts[3:])
            else:
                raise ValueError(f"Unexpected raw.githubusercontent URL format: {url}")
            repo_url = f"https://github.com/{owner}/{repo}"
            repo_name = repo

        else:
            raise ValueError(f"Only GitHub URLs are supported: {url}")

        return repo_url, repo_name, branch, file_path

    def build_deepesdl_notebook_href_from_github(
        self,
        jupyter_notebook_url: str,
        base_redirect: str = DEEPESDL_GIT_PULL_BASE,
        branch_override: str | None = None,
    ) -> str:
        """
        Build DeepESDL git-pull redirect from a full GitHub notebook URL.
        {base}?repo=<repo_url>&urlpath=lab/tree/<repo_name>/<path>&branch=<branch>
        """
        repo_url, repo_name, branch, file_path = self._parse_github_notebook_url(
            jupyter_notebook_url
        )
        if branch_override:
            branch = branch_override

        params = {
            "repo": repo_url,
            "urlpath": f"lab/tree/{repo_name}/{file_path}",
            "branch": branch,
        }
        return f"{base_redirect}?{urlencode(params, quote_via=quote)}"

    def make_related_link_for_opening_jnb_from_github(
        self,
        jupyter_notebook_url: str,
        title: str = "Open notebook on the DeepESDL platform",
        branch_override: str | None = None,
    ) -> dict[str, str]:
        return [
            {
                "rel": "related",
                "href": self.build_deepesdl_notebook_href_from_github(
                    jupyter_notebook_url, branch_override=branch_override
                ),
                "type": "text/html",
                "title": title,
            }
        ]


class WorkflowAsOgcRecord(MappingConstructible["OgcRecord"], JsonSerializable):
    def __init__(
        self,
        id: str,
        type: str,
        title: str,
        jupyter_notebook_url: str,
        properties: RecordProperties,
        links: list[dict],
        linkTemplates: list = [],
        conformsTo: list[str] = None,
        geometry: Optional[Any] = None,
        themes: Optional[Any] = None,
    ):
        if conformsTo is None:
            conformsTo = [
                OGC_API_RECORD_SPEC,
                APPLICATION_TYPE_JUPYTER_SPEC,
                APPLICATION_STAC_EXTENSION_SPEC,
            ]
        self.id = id
        self.type = type
        self.title = title
        self.jupyter_notebook_url = jupyter_notebook_url
        self.geometry = geometry
        self.properties = properties
        self.linkTemplates = linkTemplates
        self.conformsTo = conformsTo
        self.themes = themes
        self.links = self._generate_static_links() + links

    def _generate_static_links(self):
        """Generates static links (root and parent) for the record."""
        return [
            {
                "rel": "root",
                "href": "../../catalog.json",
                "type": "application/json",
                "title": "Open Science Catalog",
            },
            {
                "rel": "parent",
                "href": "../catalog.json",
                "type": "application/json",
                "title": "Workflows",
            },
            {
                "rel": "jupyter-notebook",
                "type": "application/json",
                "title": "Jupyter Notebook",
                "href": f"{self.jupyter_notebook_url}",
            },
            {
                "rel": "application-originating-platform",
                "title": "DeepESDL platform",
                "href": "https://deep.earthsystemdatalab.net/",
                "type": "text/html",
                "application:platform_supports": ["jupyter-notebook"],
                "application:preferred_app": "JupyterLab",
            },
            {
                "rel": "related",
                "href": f"../../projects/{PROJECT_COLLECTION_NAME}/collection.json",
                "type": "application/json",
                "title": "Project: DeepESDL",
            },
            {
                "rel": "self",
                "href": f"{BASE_URL_OSC}/workflows/{self.id}/record.json",
                "type": "application/json",
            },
        ]


class ExperimentAsOgcRecord(MappingConstructible["OgcRecord"], JsonSerializable):
    def __init__(
        self,
        id: str,
        title: str,
        type: str,
        jupyter_notebook_url: str,
        collection_id: str,
        properties: RecordProperties,
        links: list[dict],
        linkTemplates=None,
        conformsTo: list[str] = None,
        geometry: Optional[Any] = None,
    ):
        if linkTemplates is None:
            linkTemplates = []
        if conformsTo is None:
            conformsTo = [OGC_API_RECORD_SPEC]
        self.id = id
        self.title = title
        self.type = type
        self.conformsTo = conformsTo
        self.jupyter_notebook_url = jupyter_notebook_url
        self.collection_id = collection_id
        self.geometry = geometry
        self.properties = properties
        self.linkTemplates = linkTemplates
        self.links = self._generate_static_links() + links

    def _generate_static_links(self):
        """Generates static links (root and parent) for the record."""
        return [
            {
                "rel": "root",
                "href": "../../catalog.json",
                "type": "application/json",
                "title": "Open Science Catalog",
            },
            {
                "rel": "parent",
                "href": "../catalog.json",
                "type": "application/json",
                "title": "Experiments",
            },
            {
                "rel": "related",
                "href": f"../../workflows/{self.id}/record.json",
                "type": "application/json",
                "title": f"Workflow: {self.title}",
            },
            {
                "rel": "related",
                "href": f"../../projects/{PROJECT_COLLECTION_NAME}/collection.json",
                "type": "application/json",
                "title": "Project: DeepESDL",
            },
            {
                "rel": "application-originating-platform",
                "title": "DeepESDL platform",
                "href": "https://deep.earthsystemdatalab.net/",
                "type": "text/html",
                "application:platform_supports": ["jupyter-notebook"],
                "application:preferred_app": "JupyterLab",
            },
            {
                "rel": "input",
                "href": "./input.yaml",
                "type": "application/yaml",
                "title": "Input parameters",
            },
            {
                "rel": "environment",
                "href": "./environment.yaml",
                "type": "application/yaml",
                "title": "Execution environment",
            },
            {
                "rel": "self",
                "href": f"{BASE_URL_OSC}/experiments/{self.id}/record.json",
                "type": "application/json",
            },
        ]
