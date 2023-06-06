# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'HMMC'
copyright = '2023, Charles-Henri Mousset'
author = 'Charles-Henri Mousset'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinxcontrib.wavedrom',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinxcontrib.svgbob',
    'sphinx.ext.graphviz',
    'sphinx.ext.todo',
]

templates_path = ['_templates']
exclude_patterns = []


# -- Options for autodoc extension -------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    # 'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}


# -- Options for Wavedrom ----------------------------------------------------


# -- Options for todo --------------------------------------------------------
todo_include_todos = True
todo_emit_warnings = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = []

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'recommonmark',
}