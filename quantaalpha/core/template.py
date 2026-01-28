from pathlib import Path
from typing import Any
import yaml
from jinja2 import Environment, FileSystemLoader, Template


class CodeTemplate:
    def __init__(self, template_path: Path):
        """
        Initialize the CodeTemplate with a path to the template file.

        :param template_path: Path to the Jinja2 template file.
        """
        self.template_path = template_path
        self.env = Environment(loader=FileSystemLoader(template_path.parent))
        self.template = self.env.get_template(template_path.name)

    def render(self, **kwargs: Any) -> str:
        """
        Render the template with the provided context.

        :param kwargs: Context variables to be used in the template.
        :return: Rendered template as a string.
        """
        return self.template.render(**kwargs)