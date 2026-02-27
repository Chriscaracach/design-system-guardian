"""
File Writer Module
Handles writing refactored CSS with backup support
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class WriteResult:
    """Result of a write operation"""
    success: bool
    file_path: Path
    backup_path: Optional[Path]
    error: Optional[str]
    
    def __str__(self):
        if self.success:
            return f"Written to {self.file_path}"
        return f"Error: {self.error}"


class FileWriter:
    """Handles writing refactored CSS files with backup support"""
    
    def __init__(self, backup_dir: str = '.ds_guardian_backup'):
        """
        Initialize file writer
        
        Args:
            backup_dir: Directory for backups (relative to project root)
        """
        self.backup_dir = backup_dir
    
    def write(self, file_path: Path, content: str, create_backup: bool = True) -> WriteResult:
        """
        Write content to file with optional backup
        
        Args:
            file_path: Path to file to write
            content: Content to write
            create_backup: Whether to create a backup
        
        Returns:
            WriteResult object
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            backup_path = None
            
            # Create backup if file exists and backup is requested
            if create_backup and file_path.exists():
                backup_path = self._create_backup(file_path)
                if backup_path is None:
                    return WriteResult(
                        success=False,
                        file_path=file_path,
                        backup_path=None,
                        error="Failed to create backup"
                    )
            
            # Write the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return WriteResult(
                success=True,
                file_path=file_path,
                backup_path=backup_path,
                error=None
            )
        
        except PermissionError:
            return WriteResult(
                success=False,
                file_path=file_path,
                backup_path=None,
                error="Permission denied"
            )
        except Exception as e:
            return WriteResult(
                success=False,
                file_path=file_path,
                backup_path=None,
                error=str(e)
            )
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup of file
        
        Args:
            file_path: Path to file to backup
        
        Returns:
            Path to backup file, or None if failed
        """
        try:
            # Create backup directory structure
            backup_root = Path.cwd() / self.backup_dir
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Preserve directory structure in backup
            relative_path = file_path.relative_to(Path.cwd())
            backup_path = backup_root / timestamp / relative_path
            
            # Create parent directories
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(file_path, backup_path)
            
            return backup_path
        
        except Exception:
            return None
    
    def restore_from_backup(self, backup_path: Path, target_path: Path) -> bool:
        """
        Restore file from backup
        
        Args:
            backup_path: Path to backup file
            target_path: Path to restore to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_path.exists():
                return False
            
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy backup to target
            shutil.copy2(backup_path, target_path)
            
            return True
        
        except Exception:
            return False
    
    def list_backups(self) -> list:
        """
        List all backup sessions
        
        Returns:
            List of backup session directories
        """
        backup_root = Path.cwd() / self.backup_dir
        
        if not backup_root.exists():
            return []
        
        sessions = []
        for item in backup_root.iterdir():
            if item.is_dir():
                sessions.append({
                    'timestamp': item.name,
                    'path': item,
                    'files': list(item.rglob('*.css'))
                })
        
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)
    
    def get_backup_size(self) -> int:
        """
        Get total size of all backups
        
        Returns:
            Total size in bytes
        """
        backup_root = Path.cwd() / self.backup_dir
        
        if not backup_root.exists():
            return 0
        
        total_size = 0
        for file_path in backup_root.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def clean_old_backups(self, keep_count: int = 5) -> int:
        """
        Remove old backup sessions, keeping only the most recent
        
        Args:
            keep_count: Number of backup sessions to keep
        
        Returns:
            Number of sessions removed
        """
        sessions = self.list_backups()
        
        if len(sessions) <= keep_count:
            return 0
        
        removed = 0
        for session in sessions[keep_count:]:
            try:
                shutil.rmtree(session['path'])
                removed += 1
            except Exception:
                continue
        
        return removed
