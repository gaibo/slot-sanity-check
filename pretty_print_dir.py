from pathlib import Path, PurePath

def pretty_print_dir(root_path: Path | str) -> None:
    """ Aesthetically print file structure, i.e. recursively show names of sub-directories and files;
        sort order is alphabetical directories first, then alphabetical files starting with extension
        NOTE: I structure this function as an initialization wrapper + recursive function instead of
              just the recursive function with default base case because each node needs to show whether
              it's the "last child", which is an inelegant bit of state to pass recursively. Instead, I
              print the edge case (root node) in this initial wrapper, then have recursive function
              "look ahead" and print only the children of each node.
    :param root_path: directory/path-like
    :return: None
    """
    if not isinstance(root_path, Path):
        root_path = Path(root_path)
    if not root_path.is_dir():
        raise ValueError(f"'{root_path.name}': can't pretty-print a non-directory")
    print(root_path.name)   # Unique starting case that won't be covered during recursion
    _pretty_print_dir_recurse(root_path, level=1)    # Note how level 1 indicates children of root


def _pretty_print_dir_recurse(dir_path: Path, level: int) -> None:
    """ Helper: recursively print children of directories; assumes node is directory whose name was already printed
    :param dir_path: Path to directory
    :param level: how deep into subdirectories we are
    :return: None
    """
    if not dir_path.is_dir():
        raise ValueError(f"'{dir_path.name}': shouldn't be recursively printing a non-directory")
    # Sort children by alphabetical directories first, then alphabetical files starting with extension!
    # NOTE: I'm being very explicit here because technically .iterdir()'s output order is undefined
    sorted_children = sorted(dir_path.iterdir(), key=lambda p: ' '+p.name if p.suffix == '' else p.suffix+p.name)
    for i, child in enumerate(sorted_children):
        if i+1 == len(sorted_children):
            # Dirty way to indicate last element
            pretty_print = _pretty_print_last_child
        else:
            pretty_print = _pretty_print_non_last_child
        pretty_print(child, level)
        if child.is_dir():
            _pretty_print_dir_recurse(child, level=level+1)


def _pretty_print_non_last_child(general_path: PurePath, level: int) -> None:
    """ Helper: aesthetically print a Path name with certain number of indentations
    :param general_path: Path
    :param level: how deep into subdirectories we are
    :return: None
    """
    print(' '*4*(level-1), end='')
    print('|-- ', end='')
    print(general_path.name, end='\n')


def _pretty_print_last_child(general_path: PurePath, level: int) -> None:
    """ Helper: aesthetically print a Path name with certain number of indentations
    :param general_path: Path
    :param level: how deep into subdirectories we are
    :return: None
    """
    print(' '*4*(level-1), end='')
    print('L__ ', end='')
    print(general_path.name, end='\n')
