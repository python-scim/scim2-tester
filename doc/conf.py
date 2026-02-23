import datetime
import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("../scim2_tester"))

# -- General configuration ------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_click",
    "sphinx_issues",
    "sphinx_paramlinks",
    "sphinxcontrib.autodoc_pydantic",
    "myst_parser",
]

templates_path = ["_templates"]
master_doc = "index"
project = "scim2-tester"
year = datetime.datetime.now().strftime("%Y")
copyright = f"{year}, Yaal Coop"
author = "Yaal Coop"
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}

version = metadata.version("scim2_tester")
language = "en"
pygments_style = "sphinx"
todo_include_todos = True
toctree_collapse = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "scim2_models": ("https://scim2-models.readthedocs.io/en/latest/", None),
    "scim2_client": ("https://scim2-client.readthedocs.io/en/latest/", None),
    "scim2_cli": ("https://scim2-cli.readthedocs.io/en/latest/", None),
    "werkzeug": ("https://werkzeug.palletsprojects.com", None),
}

# -- Options for HTML output ----------------------------------------------

html_theme = "shibuya"
# html_static_path = ["_static"]
html_baseurl = "https://scim2-tester.readthedocs.io"
html_logo = "_static/python-scim.svg"
html_theme_options = {
    "globaltoc_expand_depth": 3,
    "accent_color": "tomato",
    "github_url": "https://github.com/python-scim/scim2-tester",
    "mastodon_url": "https://toot.aquilenet.fr/@yaal",
    "nav_links": [
        {"title": "scim2-models", "url": "https://scim2-models.readthedocs.io"},
        {
            "title": "scim2-client",
            "url": "https://scim2-client.readthedocs.io",
        },
        {
            "title": "scim2-cli",
            "url": "https://scim2-cli.readthedocs.io",
        },
        {
            "title": "scim2-server",
            "url": "https://github.com/python-scim/scim2-server",
        },
        {
            "title": "pytest-scim2-server",
            "url": "https://github.com/pytest-dev/pytest-scim2-server",
        },
    ],
}

# -- Options for sphinx-issues -------------------------------------

issues_github_path = "python-scim/scim2-models"
