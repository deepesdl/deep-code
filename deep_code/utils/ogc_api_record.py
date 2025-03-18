from typing import Any, Optional

from xrlint.util.constructible import MappingConstructible
from xrlint.util.serializable import JsonSerializable, JsonValue

from deep_code.constants import (
    BASE_URL_OSC,
    OGC_API_RECORD_SPEC,
    PROJECT_COLLECTION_NAME,
)


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
        return data


class LinksBuilder:
    def __init__(self, themes: list[str]):
        self.themes = themes
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
    def build_link_to_dataset(collection_id):
        return [
            {
                "rel": "child",
                "href": f"../../products/{collection_id}/collection.json",
                "type": "application/json",
                "title": f"{collection_id}",
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
            conformsTo = [OGC_API_RECORD_SPEC]
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
                "rel": "child",
                "href": f"../../experiments/{self.id}/record.json",
                "type": "application/json",
                "title": f"{self.title}",
            },
            {
                "rel": "jupyter-notebook",
                "type": "application/json",
                "title": "Jupyter Notebook",
                "href": f"{self.jupyter_notebook_url}",
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
                "rel": "child",
                "href": f"../../products/{self.collection_id}/collection.json",
                "type": "application/json",
                "title": f"{self.collection_id}",
            },
            {
                "rel": "related",
                "href": f"../../projects/{PROJECT_COLLECTION_NAME}/collection.json",
                "type": "application/json",
                "title": "Project: DeepESDL",
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
