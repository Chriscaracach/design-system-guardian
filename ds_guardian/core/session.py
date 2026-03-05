"""
Session Manager Module
Tracks refactoring session and stores results for batch review
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class FileChange:
    """Represents a refactored file"""
    file_path: str
    relative_path: str
    original_css: str
    refactored_css: str
    tokens_used: int
    lines_added: int
    lines_removed: int
    status: str  # 'pending', 'accepted', 'rejected', 'skipped'
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


class RefactoringSession:
    """Manages a refactoring session with multiple files"""
    
    def __init__(self, target_dir: Path = None, session_file: str = '.ds_guardian_session.json'):
        """
        Initialize session
        
        Args:
            target_dir: Root of the project being refactored (session file lives here)
            session_file: Session filename (resolved inside target_dir)
        """
        root = Path(target_dir) if target_dir else Path.cwd()
        self.session_file = root / session_file
        self.changes: List[FileChange] = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'total_files': 0,
            'total_tokens': 0,
            'rules_file': None,
            'target_dir': None
        }
    
    def add_change(self, change: FileChange):
        """Add a file change to the session"""
        self.changes.append(change)
        self.metadata['total_files'] = len(self.changes)
        self.metadata['total_tokens'] += change.tokens_used
    
    def save(self):
        """Save session to file"""
        data = {
            'metadata': self.metadata,
            'changes': [change.to_dict() for change in self.changes]
        }
        
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load(cls, target_dir: Path = None, session_file: str = '.ds_guardian_session.json'):
        """Load session from file"""
        session = cls(target_dir=target_dir, session_file=session_file)
        
        if not session.session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")
        
        with open(session.session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        session.metadata = data['metadata']
        session.changes = [FileChange.from_dict(c) for c in data['changes']]
        
        return session
    
    def get_pending_changes(self) -> List[FileChange]:
        """Get all pending changes"""
        return [c for c in self.changes if c.status == 'pending']
    
    def get_accepted_changes(self) -> List[FileChange]:
        """Get all accepted changes"""
        return [c for c in self.changes if c.status == 'accepted']
    
    def get_rejected_changes(self) -> List[FileChange]:
        """Get all rejected changes"""
        return [c for c in self.changes if c.status == 'rejected']
    
    def get_skipped_changes(self) -> List[FileChange]:
        """Get all skipped changes"""
        return [c for c in self.changes if c.status == 'skipped']
    
    def update_status(self, index: int, status: str):
        """Update status of a change"""
        if 0 <= index < len(self.changes):
            self.changes[index].status = status
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            'total': len(self.changes),
            'pending': len(self.get_pending_changes()),
            'accepted': len(self.get_accepted_changes()),
            'rejected': len(self.get_rejected_changes()),
            'skipped': len(self.get_skipped_changes()),
            'total_tokens': self.metadata['total_tokens'],
            'total_added': sum(c.lines_added for c in self.changes),
            'total_removed': sum(c.lines_removed for c in self.changes)
        }
    
    def clear(self):
        """Clear the session"""
        if self.session_file.exists():
            self.session_file.unlink()
    
    def exists(self) -> bool:
        """Check if session file exists"""
        return self.session_file.exists()
