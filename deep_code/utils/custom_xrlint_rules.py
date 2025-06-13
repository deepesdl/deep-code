# Copyright © 2025 Brockmann Consult GmbH.
# This software is distributed under the terms and conditions of the
# MIT license (https://mit-license.org/).

"""
This module defines the deepcode plugin for XRLint, which validates
metadata required for dataset publication to a catalog. It checks for:
- A 'description' attribute in dataset.attrs
- A 'gcmd_keyword_url' attribute in each variable's attrs
"""

from xrlint.node import DatasetNode, VariableNode
from xrlint.plugin import new_plugin
from xrlint.rule import RuleContext, RuleOp

plugin = new_plugin(name="deepcode", version="1.0.0")


@plugin.define_rule("dataset-description")
class DatasetDescriptionRule(RuleOp):
    """Ensures the dataset has a 'description' attribute."""

    def validate_dataset(self, ctx: RuleContext, node: DatasetNode):
        if "description" not in node.dataset.attrs:
            ctx.report(
                "Dataset missing required 'description' attribute.",
                suggestions=["Add a 'description' attribute to dataset.attrs."],
            )


@plugin.define_rule("variable-gcmd-keyword-url")
class VariableGcmdKeywordUrlRule(RuleOp):
    """Ensures all variables have a 'gcmd_keyword_url' attribute."""

    def validate_variable(self, ctx: RuleContext, node: VariableNode):
        if node.name not in ctx.dataset.data_vars:
            return

        if "gcmd_keyword_url" not in node.array.attrs:
            ctx.report(f"Variable '{node.name}' missing 'gcmd_keyword_url' attribute.")


# Define the recommended ruleset for this plugin
plugin.define_config(
    "recommended",
    [
        {
            "rules": {
                "deepcode/variable-gcmd-keyword-url": "error",
                "deepcode/dataset-description": "error",
            }
        }
    ],
)


def export_config() -> list:
    """
    Export the plugin configuration to be consumed by the XRLint Linter.

    Returns
    -------
    list
        A list of plugin config dictionaries and rule presets.
    """
    return [
        {"plugins": {"deepcode": plugin}},
        "recommended",
        {
            "rules": {
                "content-desc": "off",
                "no-empty-attrs": "off",
                "conventions": "off",
                "time-coordinate": "off"
            }
        },
        "deepcode/recommended",
    ]
