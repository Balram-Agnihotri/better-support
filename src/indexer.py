"""Repository indexing and symbol search."""

import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.config import Config, AccessConfig

logger = logging.getLogger(__name__)


# Constants
INDEX_MAX_FILE_BYTES = 1_500_000
READ_MAX_LINES = 260
SEARCH_MAX_RESULTS = 30

# Track indexed repositories in this session
_INDEXED_REPOS: Dict[str, 'Indexer'] = {}


@dataclass
class Symbol:
    """Represents a code symbol (class, function, etc.)."""
    name: str
    kind: str
    path: str
    line: int
    signature: str


# Symbol patterns for lightweight indexing
SYMBOL_PATTERNS = [
    ("class", re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)")),
    ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)")),
    ("type", re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)")),
    ("enum", re.compile(r"^\s*(?:export\s+)?enum\s+([A-Za-z_$][\w$]*)")),
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)")),
    ("const", re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)")),
    ("method", re.compile(r"^\s*(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*[:{]")),
]


class Indexer:
    """Repository indexer for files and symbols."""
    
    def __init__(self, repo_root: Path, access_config: AccessConfig):
        self.repo_root = repo_root
        self.access_config = access_config
        self.file_index: List[str] = []
        self.symbols: List[Symbol] = []
        self.symbols_by_file: Dict[str, List[Symbol]] = {}
    
    @classmethod
    def get_or_create(cls, repo_root: Path, access_config: AccessConfig, force_rebuild: bool = False) -> 'Indexer':
        """
        Get cached indexer or create and cache a new one.
        
        Args:
            repo_root: Repository root path
            access_config: Access configuration
            force_rebuild: Force rebuilding the index even if cached
        
        Returns:
            Indexer instance (cached or new)
        """
        repo_key = str(repo_root.resolve())
        
        if not force_rebuild and repo_key in _INDEXED_REPOS:
            logger.info(f"Using cached index for {repo_root.name}")
            return _INDEXED_REPOS[repo_key]
        
        logger.info(f"Building new index for {repo_root.name}")
        indexer = cls(repo_root, access_config)
        indexer.build_index()
        _INDEXED_REPOS[repo_key] = indexer
        return indexer
    
    def build_index(self) -> None:
        """Build lightweight index of files and symbols."""
        t0 = time.time()
        files = []
        syms = []
        scanned = 0
        
        for rel, full in self.iter_repo_files():
            files.append(rel)
            
            if full.suffix.lower() not in self.access_config.code_extensions:
                continue
            
            try:
                if full.stat().st_size > INDEX_MAX_FILE_BYTES:
                    continue
                
                with open(full, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        for kind, pat in SYMBOL_PATTERNS:
                            m = pat.match(line)
                            if m:
                                name = m.group(1)
                                syms.append(Symbol(
                                    name=name,
                                    kind=kind,
                                    path=rel,
                                    line=i,
                                    signature=line.strip()[:220]
                                ))
                                break
                
                scanned += 1
            except Exception as e:
                logger.debug(f"Failed to scan {rel}: {e}")
        
        self.file_index = sorted(files)
        self.symbols = syms
        self.symbols_by_file = {}
        for s in self.symbols:
            self.symbols_by_file.setdefault(s.path, []).append(s)
        
        logger.info(
            f"Indexed {len(self.file_index):,} files, "
            f"scanned {scanned:,} text/code files, "
            f"found {len(self.symbols):,} symbols in {time.time()-t0:.1f}s"
        )
    
    def iter_repo_files(self):
        """Iterate over non-denied files in the repository."""
        for dirpath, dirnames, filenames in os.walk(self.repo_root):
            # Filter out denied directories
            dirnames[:] = [
                d for d in dirnames
                if d not in self.access_config.deny_dir_names
            ]
            
            for name in filenames:
                full = Path(dirpath) / name
                rel = str(full.relative_to(self.repo_root)).replace("\\", "/")
                
                if self.is_denied_path(rel):
                    continue
                
                yield rel, full
    
    def is_denied_path(self, rel: str) -> bool:
        """Check if a path is denied by access rules."""
        rel = rel.replace("\\", "/").lstrip("/")
        parts = rel.split("/")
        
        # Check directory names
        if any(p in self.access_config.deny_dir_names for p in parts):
            return True
        
        # Check file patterns
        name = parts[-1] if parts else rel
        for pat in self.access_config.deny_file_patterns:
            # Simple pattern matching
            if "*" in pat:
                # Convert glob to regex
                regex_pat = pat.replace(".", r"\.").replace("*", ".*")
                if re.match(regex_pat, name) or re.match(regex_pat, rel):
                    return True
            else:
                if pat in name or pat in rel:
                    return True
        
        return False
    
    def safe_path(self, path: str) -> Tuple[str, Path]:
        """Validate and resolve a path within the repository."""
        rel = path.strip().lstrip("/").replace("\\", "/")
        full = (self.repo_root / rel).resolve()
        root = self.repo_root.resolve()
        
        if full != root and not str(full).startswith(str(root) + os.sep):
            raise ValueError(f"path escapes repo root: {path}")
        
        if self.is_denied_path(rel):
            raise ValueError(f"path denied: {rel}")
        
        return rel, full
    
    def search_symbols(self, query: str, max_results: int = 15) -> List[Symbol]:
        """Search symbols by name with fuzzy matching."""
        q = query.lower().strip()
        q_tokens = self.tokenize_identifier(query)
        scored = []
        
        for sym in self.symbols:
            name_l = sym.name.lower()
            sym_tokens = self.tokenize_identifier(sym.name)
            score = 0
            
            if name_l == q:
                score = 100
            elif q and name_l.startswith(q):
                score = 75
            elif q and q in name_l:
                score = 45
            else:
                overlap = len(set(q_tokens) & set(sym_tokens))
                if overlap:
                    score = 25 + overlap * 10
            
            # Bonus for path relevance
            path_tokens = self.tokenize_identifier(sym.path)
            score += len(set(q_tokens) & set(path_tokens)) * 4
            
            if score > 0:
                scored.append((score, sym))
        
        scored.sort(key=lambda x: (-x[0], x[1].path, x[1].line))
        return [s for _, s in scored[:max_results]]
    
    def tokenize_identifier(self, name: str) -> List[str]:
        """Tokenize an identifier for fuzzy matching."""
        parts = re.split(r"[^A-Za-z0-9]+", name)
        out = []
        
        for part in parts:
            if not part:
                continue
            
            # Split camelCase
            part = re.sub(r"([a-z])([A-Z])", r"\1 \2", part)
            part = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", part)
            
            out.extend(w.lower() for w in part.split() if len(w) > 1)
        
        return out
    
    def identifier_forms(self, query: str) -> List[str]:
        """Generate different forms of an identifier for search."""
        toks = self.tokenize_identifier(query)
        forms = []
        
        for i in range(len(toks) - 1):
            a, b = toks[i], toks[i + 1]
            forms.append(f"{a}_{b}")  # snake_case
            forms.append(a + b[:1].upper() + b[1:])  # camelCase
        
        forms.extend(toks)
        
        for a in toks:
            for b in toks:
                if a != b:
                    forms.append(f"{a}_{b}")
        
        # Deduplicate while preserving order
        seen = []
        for f in forms:
            if f and f not in seen:
                seen.append(f)
        
        return seen[:12]


def clamp_text(s: str, n: int = 6000) -> str:
    """Clamp text to a maximum length."""
    return s if len(s) <= n else s[:n] + f"\n... [truncated {len(s)-n} chars]"
