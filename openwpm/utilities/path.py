from pathlib import Path


def path_from_home(path: str) -> str:
    """Generates the absolute path from Ubuntu home directory if using a ~ symbol

    Args:
        path (str): The relative path to the home directory

    Returns:
        str: the aboslute path
    """
    return path.replace("~", str(Path.home()))
