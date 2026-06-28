"""Tool implementations for BetterCode agent."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.indexer import Indexer, clamp_text, Symbol, READ_MAX_LINES, SEARCH_MAX_RESULTS

logger = logging.getLogger(__name__)


class Workspace:
    """Workspace state for tracking searches, reads, and findings."""
    
    def __init__(self):
        self.searches: List[str] = []
        self.files_read: Dict[str, Dict[str, Any]] = {}
        self.findings: List[Dict[str, Any]] = []
        self.hypothesis: str = ""
    
    def reset(self):
        """Reset workspace state."""
        self.searches.clear()
        self.files_read.clear()
        self.findings.clear()
        self.hypothesis = ""


class Tools:
    """BetterCode tool implementations."""
    
    def __init__(self, indexer: Indexer, workspace: Workspace):
        self.indexer = indexer
        self.workspace = workspace
        self.repo_root = indexer.repo_root
    
    def search(
        self,
        query: str = "",
        path: Optional[str] = None,
        glob: Optional[str] = None,
        maxResults: int = 20,
        contextLines: int = 2
    ) -> Dict[str, Any]:
        """Search the repository for code, text, symbols, or files."""
        query = (query or "").strip()
        maxResults = min(maxResults or SEARCH_MAX_RESULTS, SEARCH_MAX_RESULTS)
        
        # If no query, list directory
        if not query:
            rel, full = self.indexer.safe_path(path or "")
            entries = []
            
            if full.is_dir():
                for p in sorted(full.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]:
                    child_rel = str(p.relative_to(self.repo_root)).replace("\\", "/")
                    if self.indexer.is_denied_path(child_rel):
                        continue
                    entries.append(child_rel + ("/" if p.is_dir() else ""))
            
            content = f'Contents of "{rel or "."}" ({len(entries)} entries):\n' + "\n".join(entries)
            return {
                "ok": True,
                "content": content,
                "citations": [],
                "meta": {"path": rel, "count": len(entries)}
            }
        
        self.workspace.searches.append(query)
        
        # Run ripgrep search
        rows = self._run_rg(query, path=path, glob=glob, max_results=maxResults * 2, context=contextLines)
        
        # Try alternative forms if few results
        tried = [query]
        if len(rows) < 3:
            for form in self.indexer.identifier_forms(query):
                if form in tried:
                    continue
                tried.append(form)
                rows.extend(self._run_rg(form, path=path, glob=glob, max_results=maxResults, context=contextLines))
                if len(rows) >= maxResults:
                    break
        
        # Search symbols
        sym_matches = self.indexer.search_symbols(query, max_results=10)
        
        # Merge results
        seen = set()
        merged = []
        
        for s in sym_matches:
            key = (s.path, s.line)
            if key not in seen:
                seen.add(key)
                merged.append({
                    "path": s.path,
                    "line": s.line,
                    "endLine": s.line,
                    "snippet": s.signature,
                    "source": f"symbol:{s.kind}",
                    "symbol": s.name
                })
        
        for r in rows:
            key = (r["path"], r["line"])
            if key not in seen:
                seen.add(key)
                merged.append(r)
        
        merged = merged[:maxResults]
        
        # Group by file
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for r in merged:
            by_file.setdefault(r["path"], []).append(r)
        
        if not merged:
            content = f'No matches found for "{query}". Tried: {", ".join(tried[:8])}'
            return {
                "ok": True,
                "content": content,
                "citations": [],
                "meta": {"query": query, "tried": tried}
            }
        
        # Build content string
        blocks = []
        for file_path, hits in list(by_file.items())[:12]:
            lines = []
            for h in hits[:6]:
                sym = f' · {h.get("source", "")}'
                lines.append(f'  L{h["line"]}{sym} — {h.get("snippet", "").strip()[:180]}')
            blocks.append(f"📄 {file_path}\n" + "\n".join(lines))
        
        # Suggest reads
        suggestions = []
        for file_path, hits in list(by_file.items())[:5]:
            start = max(1, min(h["line"] for h in hits) - 12)
            end = max(h["line"] for h in hits) + 60
            suggestions.append(f'read(path="{file_path}", startLine={start}, endLine={end})')
        
        content = (
            f'Searched for "{query}". Found {len(merged)} result(s) across {len(by_file)} file(s).\n'
            f'Tried patterns: {", ".join(tried[:8])}\n\n'
            + "\n\n".join(blocks)
            + "\n\nSuggested reads:\n"
            + "\n".join(suggestions)
        )
        
        citations = [
            {"path": r["path"], "startLine": r["line"], "endLine": r.get("endLine", r["line"])}
            for r in merged
        ]
        
        return {
            "ok": True,
            "content": content,
            "citations": citations,
            "meta": {"query": query, "returned": len(merged)}
        }
    
    def read(
        self,
        path: str,
        startLine: Optional[int] = None,
        endLine: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read a file or targeted line range."""
        rel, full = self.indexer.safe_path(path)
        
        if not full.exists():
            return {"ok": False, "content": f"ERROR: file not found: {rel}", "citations": []}
        
        if full.is_dir():
            return {
                "ok": False,
                "content": f"ERROR: {rel} is a directory. Use search(query='', path='{rel}') to list it.",
                "citations": []
            }
        
        if full.stat().st_size > 5_000_000:
            return {
                "ok": False,
                "content": f"ERROR: file too large: {rel}. Use search first, then read a small range.",
                "citations": []
            }
        
        lines = full.read_text(encoding="utf-8", errors="ignore").splitlines()
        total = len(lines)
        start = max(1, int(startLine or 1))
        requested_end = int(endLine or min(total, start + READ_MAX_LINES - 1))
        end = min(total, requested_end, start + READ_MAX_LINES - 1)
        
        numbered = "\n".join(f"{i}\t{lines[i-1]}" for i in range(start, end + 1))
        content = f"{rel} (lines {start}-{end} of {total})\n{numbered}"
        
        self.workspace.files_read[rel] = {
            "start": start,
            "end": end,
            "excerpt": clamp_text(numbered, 1200)
        }
        
        return {
            "ok": True,
            "content": content,
            "citations": [{"path": rel, "startLine": start, "endLine": end}],
            "meta": {"path": rel, "startLine": start, "endLine": end, "totalLines": total}
        }
    
    def workspaceSymbols(self, query: str, maxResults: int = 25) -> Dict[str, Any]:
        """Fuzzy search repository symbols by name."""
        matches = self.indexer.search_symbols(query, max_results=maxResults)
        content = "\n".join(
            f'{s.kind} `{s.name}` — {s.path}:L{s.line} — {s.signature[:160]}'
            for s in matches
        )
        
        return {
            "ok": True,
            "content": content or f"No symbols matched {query}",
            "citations": [{"path": s.path, "startLine": s.line, "endLine": s.line} for s in matches]
        }
    
    def findSymbol(
        self,
        name: str,
        kind: Optional[str] = None,
        fuzzy: bool = True,
        maxResults: int = 20
    ) -> Dict[str, Any]:
        """Find a specific symbol by name."""
        matches = self.indexer.search_symbols(name, max_results=maxResults)
        
        if kind:
            matches = [m for m in matches if m.kind == kind]
        
        content = "\n".join(
            f'{s.kind} `{s.name}` — {s.path}:L{s.line} — {s.signature[:160]}'
            for s in matches
        )
        
        return {
            "ok": True,
            "content": content or f"No symbol named {name}",
            "citations": [{"path": s.path, "startLine": s.line, "endLine": s.line} for s in matches]
        }
    
    def documentSymbols(self, path: str) -> Dict[str, Any]:
        """List symbols in a file without reading the whole file."""
        rel, _ = self.indexer.safe_path(path)
        syms = self.indexer.symbols_by_file.get(rel, [])
        
        content = "\n".join(
            f'L{s.line}: {s.kind} `{s.name}` — {s.signature[:160]}'
            for s in syms
        )
        
        return {
            "ok": True,
            "content": content or f"No symbols indexed in {rel}",
            "citations": [{"path": s.path, "startLine": s.line, "endLine": s.line} for s in syms]
        }
    
    def findReferences(self, symbol: str, maxResults: int = 30) -> Dict[str, Any]:
        """Find approximate references/usages of a symbol via text search."""
        return self.search(query=symbol, maxResults=maxResults, contextLines=1)
    
    def recordFinding(
        self,
        text: str,
        evidence: Optional[List[str]] = None,
        confidence: str = "medium"
    ) -> Dict[str, Any]:
        """Record an important discovery with evidence."""
        evidence = evidence or []
        self.workspace.findings.append({
            "text": text,
            "evidence": evidence,
            "confidence": confidence
        })
        
        content = f"Recorded finding: {text}\nEvidence: {', '.join(evidence)}\nConfidence: {confidence}"
        return {"ok": True, "content": content, "citations": []}
    
    def updateHypothesis(self, text: str) -> Dict[str, Any]:
        """Update your current concise working hypothesis."""
        self.workspace.hypothesis = text
        return {"ok": True, "content": f"Updated hypothesis: {text}", "citations": []}
    
    def getWorkspaceSummary(self) -> Dict[str, Any]:
        """Review searches, files read, findings, and hypothesis before final answer."""
        parts = []
        
        if self.workspace.hypothesis:
            parts.append("Hypothesis:\n" + self.workspace.hypothesis)
        
        if self.workspace.findings:
            parts.append("Findings:\n" + "\n".join(
                f'- {f["text"]} ({f["confidence"]}) evidence={", ".join(f["evidence"])}'
                for f in self.workspace.findings
            ))
        
        if self.workspace.files_read:
            parts.append("Files read:\n" + "\n".join(
                f'- {p}:L{v["start"]}-L{v["end"]}'
                for p, v in self.workspace.files_read.items()
            ))
        
        if self.workspace.searches:
            parts.append("Searches:\n" + "\n".join(
                f'- {q}' for q in self.workspace.searches[-10:]
            ))
        
        content = "\n\n".join(parts) or "Workspace is empty."
        return {"ok": True, "content": content, "citations": []}
    
    def _run_rg(
        self,
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        max_results: int = 30,
        context: int = 2
    ) -> List[Dict[str, Any]]:
        """Run ripgrep search."""
        args = ["rg", "--json", "--smart-case", "--max-columns", "300", "--fixed-strings"]
        
        if context:
            args += ["--context", str(context)]
        
        if glob:
            args += ["--glob", glob]
        
        # Add deny globs
        for d in self.indexer.access_config.deny_dir_names:
            args += ["--glob", f"!**/{d}/**"]
        
        for pat in self.indexer.access_config.deny_file_patterns:
            args += ["--glob", f"!{pat}"]
        
        args += ["-e", pattern]
        
        if path:
            _, full = self.indexer.safe_path(path)
            args.append(str(full.relative_to(self.repo_root)))
        else:
            args.append(".")
        
        try:
            proc = subprocess.run(
                args,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=30
            )
        except subprocess.TimeoutExpired:
            logger.warning("ripgrep search timed out")
            return []
        
        rows = []
        for line in proc.stdout.splitlines():
            if len(rows) >= max_results:
                break
            
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            if evt.get("type") != "match":
                continue
            
            data = evt.get("data", {})
            rel = data.get("path", {}).get("text", "").lstrip("./")
            
            if not rel or self.indexer.is_denied_path(rel):
                continue
            
            line_no = data.get("line_number", 1)
            text = data.get("lines", {}).get("text", "").rstrip("\n")
            
            rows.append({
                "path": rel,
                "line": line_no,
                "snippet": text[:300],
                "source": "rg"
            })
        
        return rows
