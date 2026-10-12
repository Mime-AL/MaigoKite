"""Compatibility imports for the filesystem helpers shared with trusted read tools."""
from agent.security.workspace_fs import create_entry, parent_directory, read_file, windows_directory

__all__ = ["create_entry", "parent_directory", "read_file", "windows_directory"]
