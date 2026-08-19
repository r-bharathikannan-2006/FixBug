from pathlib import Path

def folder_validation(file_path: str, folder_path: str) -> bool:
    """Validates whether a target file resolves safely within a specified base directory.

    Args:
        file_path (str): The relative or absolute path of the target file.
        folder_path (str): The base directory path serving as the boundary limit.

    Returns:
        bool: True if the resolved file path resides strictly within the base directory, False otherwise.
    """
    file_p = (Path(folder_path) / file_path).resolve()
    folder_p = Path(folder_path).resolve()
    
    # Prevent directory traversal by resolving absolute paths and verifying containment
    return file_p.is_relative_to(folder_p)