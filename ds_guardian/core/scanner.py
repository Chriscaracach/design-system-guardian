"""
File Scanner Module
Scans directories for CSS, SCSS, and LESS files
"""

import os
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class StyleFile:
    """Represents a style file found during scanning"""
    path: Path
    relative_path: Path
    size: int
    extension: str
    
    def __str__(self):
        return f"{self.relative_path} ({self.size} bytes)"


class FileScanner:
    """Scans directories for style files"""
    
    STYLE_EXTENSIONS = {'.css', '.scss', '.sass', '.less'}

    DS_GUARDIAN_FILES = {
        'design_system.css',
        'palette.css',
        'fonts.css',
        'spacing.css',
        'borders.css',
        'shadows.css',
        'motion.css',
    }
    
    def __init__(self, root_dir: str = '.'):
        """
        Initialize scanner
        
        Args:
            root_dir: Root directory to scan (default: current directory)
        """
        self.root_dir = Path(root_dir).resolve()
        
        if not self.root_dir.exists():
            raise ValueError(f"Directory does not exist: {self.root_dir}")
        
        if not self.root_dir.is_dir():
            raise ValueError(f"Not a directory: {self.root_dir}")
    
    def scan(self, exclude_patterns: List[str] = None) -> List[StyleFile]:
        """
        Scan directory for style files
        
        Args:
            exclude_patterns: List of patterns to exclude (e.g., ['node_modules', 'dist'])
        
        Returns:
            List of StyleFile objects
        """
        if exclude_patterns is None:
            exclude_patterns = [
                'node_modules',
                'dist',
                'build',
                '.git',
                'venv',
                'env',
                '.venv',
                '__pycache__',
                'vendor',
                'bower_components',
                '.next',
                '.nuxt',
                'coverage',
                '.cache'
            ]
        
        files = []
        
        for root, dirs, filenames in os.walk(self.root_dir):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._should_exclude(d, exclude_patterns)]
            
            # Check each file
            for filename in filenames:
                file_path = root_path / filename
                
                # Check if it's a style file
                if file_path.suffix.lower() in self.STYLE_EXTENSIONS:
                    # Skip DS Guardian output files
                    if filename in self.DS_GUARDIAN_FILES:
                        continue
                    # Skip if in excluded directory
                    if not self._is_in_excluded_dir(file_path, exclude_patterns):
                        try:
                            size = file_path.stat().st_size
                            relative = file_path.relative_to(self.root_dir)
                            
                            files.append(StyleFile(
                                path=file_path,
                                relative_path=relative,
                                size=size,
                                extension=file_path.suffix.lower()
                            ))
                        except (OSError, ValueError):
                            continue
        
        return sorted(files, key=lambda f: f.relative_path)
    
    def _should_exclude(self, dirname: str, patterns: List[str]) -> bool:
        """Check if directory should be excluded"""
        dirname_lower = dirname.lower()
        return any(pattern.lower() in dirname_lower for pattern in patterns)
    
    def _is_in_excluded_dir(self, file_path: Path, patterns: List[str]) -> bool:
        """Check if file is in an excluded directory"""
        parts = [p.lower() for p in file_path.parts]
        return any(
            any(pattern.lower() in part for pattern in patterns)
            for part in parts
        )
    
    def get_summary(self, files: List[StyleFile]) -> Dict:
        """
        Get summary statistics about scanned files
        
        Args:
            files: List of StyleFile objects
        
        Returns:
            Dictionary with summary statistics
        """
        if not files:
            return {
                'total_files': 0,
                'total_size': 0,
                'by_extension': {},
                'largest_file': None
            }
        
        by_extension = {}
        total_size = 0
        
        for file in files:
            ext = file.extension
            if ext not in by_extension:
                by_extension[ext] = {'count': 0, 'size': 0}
            
            by_extension[ext]['count'] += 1
            by_extension[ext]['size'] += file.size
            total_size += file.size
        
        largest = max(files, key=lambda f: f.size)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'by_extension': by_extension,
            'largest_file': largest
        }
    
    def filter_by_extension(self, files: List[StyleFile], extension: str) -> List[StyleFile]:
        """
        Filter files by extension
        
        Args:
            files: List of StyleFile objects
            extension: Extension to filter by (e.g., '.css')
        
        Returns:
            Filtered list of StyleFile objects
        """
        if not extension.startswith('.'):
            extension = f'.{extension}'
        
        return [f for f in files if f.extension == extension.lower()]
    
    def filter_by_size(self, files: List[StyleFile], min_size: int = 0, max_size: int = None) -> List[StyleFile]:
        """
        Filter files by size
        
        Args:
            files: List of StyleFile objects
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes (None for no limit)
        
        Returns:
            Filtered list of StyleFile objects
        """
        filtered = [f for f in files if f.size >= min_size]
        
        if max_size is not None:
            filtered = [f for f in filtered if f.size <= max_size]
        
        return filtered


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
