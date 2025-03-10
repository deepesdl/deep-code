from typing import Any, Optional

from xrlint.util.constructible import MappingConstructible
from xrlint.util.serializable import JsonSerializable, JsonValue

from deep_code.constants import OGC_API_RECORD_SPEC, BASE_URL_OSC


class Contact(MappingConstructible["Contact"], JsonSerializable):
    def __init__(
        self,
        name: str,
        organization: str,
        position: str | None = "",
        links: list[dict[str, Any]] | None = None,
        contactInstructions: str | None = "",
        roles: list[str] = None,
    ):
        self.name = name
        self.organization = organization
        self.position = position
        self.links = links or []
        self.contactInstructions = contactInstructions
        self.roles = roles or ["principal investigator"]


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
        self.keywords = keywords or []
        self.contacts = contacts
        self.themes = themes
        self.formats = formats or []
        self.license = license


class ExperimentAsOgcRecord(MappingConstructible["OgcRecord"], JsonSerializable):
    def __init__(
        self,
        id: str,
        type: str,
        jupyter_notebook_url: str,
        properties: RecordProperties,
        links: list[dict],
        linkTemplates: list = [],
        conformsTo: list[str] = None,
        geometry: Optional[Any] = None
    ):
        if conformsTo is None:
            conformsTo = [OGC_API_RECORD_SPEC]
        self.id = id
        self.type = type
        self.conformsTo = conformsTo
        self.jupyter_notebook_url = jupyter_notebook_url
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
                "title": "Open Science Catalog"
            },
            {
                "rel": "parent",
                "href": "../catalog.json",
                "type": "application/json",
                "title": "Experiments"
            },
            {
                "rel": "related",
                "href": f"../../workflows/{self.id}/record.json",
                "type": "application/json",
                "title": "Workflow: POLARIS"
            },
            {
                "rel": "related",
                "href": "../../projects/deepesdl/collection.json",
                "type": "application/json",
                "title": "Project: DeepESDL"
            },
            {
                "rel": "input",
                "href": "./input.yaml",
                "type": "application/yaml",
                "title": "Input parameters"
            },
            {
                "rel": "environment",
                "href": "./environment.yaml",
                "type": "application/yaml",
                "title": "Execution environment"
            },
            {
                "rel": "self",
                "href": f"{BASE_URL_OSC}/experiments/{self.id}/record.json",
                "type": "application/json"
            }
        ]

class WorkflowAsOgcRecord(MappingConstructible["OgcRecord"], JsonSerializable):
    def __init__(
        self,
        id: str,
        type: str,
        jupyter_notebook_url: str,
        properties: RecordProperties,
        links: list[dict],
        linkTemplates: list = [],
        conformsTo: list[str] = None,
        geometry: Optional[Any] = None
    ):
        if conformsTo is None:
            conformsTo = [OGC_API_RECORD_SPEC]
        self.id = id
        self.type = type
        self.conformsTo = conformsTo
        self.jupyter_notebook_url = jupyter_notebook_url
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
                "title": "Open Science Catalog"
            },
            {
                "rel": "parent",
                "href": "../catalog.json",
                "type": "application/json",
                "title": "Workflows"
            },
            {
                "rel": "child",
                "href": f"../../experiments/{self.id}/record.json",
                "type": "application/json",
                "title": f"{self.id}"
            },
            {
                "rel": "jupyter-notebook",
                "type": "application/json",
                "title": "Jupyter Notebook",
                "href": f"{self.jupyter_notebook_url}"
            },

            {
                "rel": "self",
                "href": f"{BASE_URL_OSC}/workflows/{self.id}/record.json",
                "type": "application/json"
            }
        ]