#!/usr/bin/env python3
"""
File utilities for DAP trace library.

Common file operations used across multiple library modules.
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import shutil

logger = logging.getLogger(__name__)


class FileUtils:
    """Utility class for file operations."""

    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """Ensure directory exists, create if it doesn't.

        Args:
            path: Directory path

        Returns:
            Path object for the directory
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def read_json(path: Union[str, Path]) -> Dict[str, Any]:
        """Read JSON file.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            JSONDecodeError: If JSON is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {path}")

        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def write_json(data: Dict[str, Any], path: Union[str, Path], indent: int = 2) -> Path:
        """Write data to JSON file.

        Args:
            data: Data to write
            path: Output file path
            indent: JSON indentation

        Returns:
            Path to written file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(data, f, indent=indent)

        logger.debug(f"Written JSON to: {path}")
        return path

    @staticmethod
    def read_yaml(path: Union[str, Path]) -> Dict[str, Any]:
        """Read YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML data

        Raises:
            FileNotFoundError: If file doesn't exist
            YAMLError: If YAML is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {path}")

        with open(path, "r") as f:
            return yaml.safe_load(f)

    @staticmethod
    def write_yaml(data: Dict[str, Any], path: Union[str, Path]) -> Path:
        """Write data to YAML file.

        Args:
            data: Data to write
            path: Output file path

        Returns:
            Path to written file
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

        logger.debug(f"Written YAML to: {path}")
        return path

    @staticmethod
    def copy_with_structure(source: Union[str, Path], target: Union[str, Path]) -> List[Path]:
        """Copy files while preserving directory structure.

        Args:
            source: Source directory or file
            target: Target directory

        Returns:
            List of copied file paths
        """
        source = Path(source)
        target = Path(target)

        copied_files = []

        if source.is_file():
            # Copy single file
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied_files.append(target)

        elif source.is_dir():
            # Copy directory recursively
            for item in source.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(source)
                    target_path = target / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_path)
                    copied_files.append(target_path)

        logger.debug(f"Copied {len(copied_files)} files from {source} to {target}")
        return copied_files

    @staticmethod
    def find_files(
        directory: Union[str, Path], pattern: str = "**/*", recursive: bool = True
    ) -> List[Path]:
        """Find files matching pattern.

        Args:
            directory: Directory to search
            pattern: Glob pattern
            recursive: Whether to search recursively

        Returns:
            List of matching file paths
        """
        directory = Path(directory)

        if not directory.exists():
            return []

        if recursive:
            return list(directory.glob(pattern))
        else:
            return list(directory.glob(pattern.split("/")[-1]))

    @staticmethod
    def find_files_by_extension(
        directory: Union[str, Path], extensions: List[str], recursive: bool = True
    ) -> List[Path]:
        """Find files by extension.

        Args:
            directory: Directory to search
            extensions: List of extensions (e.g., [".py", ".json"])
            recursive: Whether to search recursively

        Returns:
            List of matching file paths
        """
        directory = Path(directory)

        if not directory.exists():
            return []

        files = []
        for ext in extensions:
            pattern = f"**/*{ext}" if recursive else f"*{ext}"
            files.extend(directory.glob(pattern))

        return sorted(set(files))

    @staticmethod
    def clean_directory(directory: Union[str, Path], keep_patterns: List[str] = None) -> int:
        """Clean directory, optionally keeping files matching patterns.

        Args:
            directory: Directory to clean
            keep_patterns: List of glob patterns to keep

        Returns:
            Number of files removed
        """
        directory = Path(directory)

        if not directory.exists():
            return 0

        # Files to keep
        keep_files = set()
        if keep_patterns:
            for pattern in keep_patterns:
                keep_files.update(directory.glob(pattern))

        # Remove files not in keep list
        removed_count = 0
        for item in directory.iterdir():
            if item in keep_files:
                continue

            if item.is_file():
                item.unlink()
                removed_count += 1
            elif item.is_dir():
                shutil.rmtree(item)
                removed_count += 1  # Count directory as one removal

        logger.debug(f"Cleaned directory {directory}, removed {removed_count} items")
        return removed_count

    @staticmethod
    def get_file_size(path: Union[str, Path]) -> int:
        """Get file size in bytes.

        Args:
            path: File path

        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        path = Path(path)
        if path.exists() and path.is_file():
            return path.stat().st_size
        return 0

    @staticmethod
    def get_directory_size(directory: Union[str, Path]) -> int:
        """Get total size of directory in bytes.

        Args:
            directory: Directory path

        Returns:
            Total size in bytes, or 0 if directory doesn't exist
        """
        directory = Path(directory)

        if not directory.exists():
            return 0

        total_size = 0
        for item in directory.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size

        return total_size

    @staticmethod
    def create_backup(source: Union[str, Path], backup_dir: Union[str, Path] = None) -> Path:
        """Create backup of file or directory.

        Args:
            source: Source file or directory
            backup_dir: Backup directory (default: source.parent / "backup")

        Returns:
            Path to backup location
        """
        source = Path(source)

        if backup_dir is None:
            backup_dir = source.parent / "backup"

        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup path with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}_{timestamp}"

        if source.is_file():
            backup_path = backup_dir / backup_name
            shutil.copy2(source, backup_path)
        else:
            backup_path = backup_dir / backup_name
            shutil.copytree(source, backup_path)

        logger.info(f"Created backup of {source} at {backup_path}")
        return backup_path

    @staticmethod
    def merge_json_files(files: List[Union[str, Path]], output_path: Union[str, Path]) -> Path:
        """Merge multiple JSON files into one.

        Args:
            files: List of JSON file paths
            output_path: Output file path

        Returns:
            Path to merged file
        """
        merged_data = {}

        for file_path in files:
            file_path = Path(file_path)
            if file_path.exists():
                try:
                    data = FileUtils.read_json(file_path)
                    # Merge with existing data
                    for key, value in data.items():
                        if key in merged_data:
                            # Handle duplicate keys
                            if isinstance(merged_data[key], list):
                                merged_data[key].append(value)
                            else:
                                merged_data[key] = [merged_data[key], value]
                        else:
                            merged_data[key] = value
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")

        return FileUtils.write_json(merged_data, output_path)

    @staticmethod
    def split_json_file(
        input_path: Union[str, Path], max_size_kb: int = 1024, output_dir: Union[str, Path] = None
    ) -> List[Path]:
        """Split large JSON file into smaller files.

        Args:
            input_path: Input JSON file
            max_size_kb: Maximum size per output file in KB
            output_dir: Output directory (default: input file directory)

        Returns:
            List of created file paths
        """
        input_path = Path(input_path)

        if output_dir is None:
            output_dir = input_path.parent

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read input data
        data = FileUtils.read_json(input_path)

        # Split logic depends on data structure
        output_files = []

        if isinstance(data, dict):
            # Split dictionary by keys
            items = list(data.items())
            chunk_size = max(
                1, len(items) // (FileUtils.get_file_size(input_path) // (max_size_kb * 1024) + 1)
            )

            for i in range(0, len(items), chunk_size):
                chunk = dict(items[i : i + chunk_size])
                output_path = output_dir / f"{input_path.stem}_part{i//chunk_size + 1}.json"
                FileUtils.write_json(chunk, output_path)
                output_files.append(output_path)

        elif isinstance(data, list):
            # Split list
            chunk_size = max(
                1, len(data) // (FileUtils.get_file_size(input_path) // (max_size_kb * 1024) + 1)
            )

            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                output_path = output_dir / f"{input_path.stem}_part{i//chunk_size + 1}.json"
                FileUtils.write_json(chunk, output_path)
                output_files.append(output_path)

        else:
            # Single item, just copy
            output_path = output_dir / f"{input_path.stem}_part1.json"
            FileUtils.write_json(data, output_path)
            output_files.append(output_path)

        logger.info(f"Split {input_path} into {len(output_files)} files")
        return output_files
