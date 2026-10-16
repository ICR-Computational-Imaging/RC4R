"""This file is used to mark the directory as a Python package.
It can be left empty or used to define package-level variables and imports."""

from importlib.metadata import version

# This allows people to check version via `import dermapred; print(dermapred.__version__)`.
__version__ = version("dermapred")