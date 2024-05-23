import os
from pathlib import Path
from typing import List, Tuple
import xml.etree.ElementTree as ET


def collect_dirlist_filelist(root_path: Path | str) -> Tuple[List[Path], List[Path]]:
    """ Return list of all nested directories and list of all files after walking it
        NOTE: I originally wrote this in Python 3.10, when pathlib didn't have Path.walk() built-in;
              this is extremely annoying, but I am importing os exclusively to use os.walk()
        NOTE: no "duplicate" names in output because full paths are used; List rather than Set to preserve walk order
    :param root_path: Path to directory
    :return: (list of dirs, list of files)
    """
    if not isinstance(root_path, Path):
        root_path = Path(root_path)
    if not root_path.is_dir():
        raise ValueError(f"'{root_path.name}': shouldn't be walking a non-directory")
    dirlist, filelist = [], []
    for root, dirs, files in os.walk(root_path):
        if dirs:
            dirlist += [Path(root)/dir_i for dir_i in dirs]
        if files:
            filelist += [Path(root)/file_i for file_i in files]
    return dirlist, filelist


def flatten_dict(nested_dict: dict, separator: str | None = '_', parent: str = '') -> dict:
    """ Flatten nested dictionary to single level of keys and values; unless separator is set to None,
        keys are casted to strings for now (I can imagine expanding to allow types with + operator
        overloading, and casting to string if it's a mix, but that seems more trouble than it's worth);
        separator is used to concatenate nested keys, keeping them unique when flattened
    :param nested_dict: Python dictionary
    :param separator: string used to concatenate parent key with nested key; set None to allow
                      overwriting values (keeping the most nested) rather than generating new keys!
    :param parent: used to pass parent key state during recursion; set '' to initialize at root
    :return: flattened dict
    """
    flattened_dict = {}
    for key, value in nested_dict.items():
        if separator is None:
            full_path_str_key = key     # Don't generate new unique key
        else:
            full_path_str_key = parent + separator + str(key) if parent else str(key)   # No separator if root
        if isinstance(value, dict):
            # Recurse
            flattened_value_dict = flatten_dict(value, separator=separator, parent=full_path_str_key)
            flattened_dict |= flattened_value_dict
        else:
            flattened_dict[full_path_str_key] = value
    return flattened_dict


def xml_dfs_get_text_set(node: ET.Element) -> set:
    """ Return set of all XML "text", i.e. strings between XML tags
    :param node: "Element" node
    :return: set of text strings
    """
    collection = set()  # Initialize empty
    _xml_dfs_helper(node, collection)
    return collection


def _xml_dfs_helper(node: ET.Element, text_set: set) -> None:
    # NOTE: "text" is anything between opening tag and closing tag; tags nesting tags 
    # to create structure in XML will just show something like '\n\t\t' as its "text"
    text = node.text.strip()
    if text:
        text_set.add(text)  # Only non-trivial text
    for child in node:
        _xml_dfs_helper(child, text_set)     # Recurse
