from typing import Any, Optional

from xrlint.util.constructible import MappingConstructible
from xrlint.util.serializable import JsonSerializable

from deep_code.constants import OGC_API_RECORD_SPEC


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
    def __init__(self, concepts: list[ThemeConcept], scheme: str):
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


class OgcRecord(MappingConstructible["OgcRecord"], JsonSerializable):
    def __init__(
        self,
        id: str,
        type: str,
        time: dict,
        properties: RecordProperties,
        links: list[dict],
        linkTemplates: list = [],
        conformsTo: list[str] = None,
        geometry: Optional[Any] = None,
    ):
        if conformsTo is None:
            conformsTo = [OGC_API_RECORD_SPEC]
        self.id = id
        self.type = type
        self.conformsTo = conformsTo
        self.time = time
        self.geometry = geometry
        self.properties = properties
        self.linkTemplates = linkTemplates
        self.links = links
