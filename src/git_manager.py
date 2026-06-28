"""Git repository management with submodule support."""

import logging
import subprocess
from pathlib import Path
from typing import Optional, Set

from src.config import ProjectConfig

logger = logging.getLogger(__name__)

# Track repos that have been initialized in this session
_INITIALIZED_REPOS: Set[str] = set()


class GitManager:
    """Manages git repository cloning and updates."""
    
    def __init__(self, projects_dir: Path):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
    
    def ensure_repo(self, project: ProjectConfig, skip_pull_if_exists: bool = True) -> Path:
        """
        Ensure repository exists and is up to date.
        
        Args:
            project: Project configuration
            skip_pull_if_exists: If True, skip git pull if repo was already initialized in this session
        
        Returns:
            Path to the repository
        """
        repo_path = self.projects_dir / project.name
        repo_key = str(repo_path)
        
        if repo_path.exists():
            if repo_key in _INITIALIZED_REPOS and skip_pull_if_exists:
                logger.info(f"Repository {project.name} already initialized in this session, skipping pull")
                return repo_path
            
            logger.info(f"Repository {project.name} already exists at {repo_path}")
            try:
                if not skip_pull_if_exists:
                    self._pull_repo(repo_path, project)
                    if project.submodules:
                        self._update_submodules(repo_path, project)
                else:
                    logger.info(f"Skipping git pull for {project.name} (already initialized)")
            except Exception as e:
                logger.warning(f"Failed to update {project.name}: {e}")
            
            _INITIALIZED_REPOS.add(repo_key)
        else:
            logger.info(f"Cloning repository {project.name} to {repo_path}")
            self._clone_repo(repo_path, project)
            if project.submodules:
                self._init_submodules(repo_path, project)
            
            _INITIALIZED_REPOS.add(repo_key)
        
        return repo_path
    
    def _clone_repo(self, repo_path: Path, project: ProjectConfig) -> None:
        """Clone a git repository."""
        clone_url = self._get_authenticated_url(project.repo_url, project.github_token)
        
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--branch", project.branch,
            clone_url,
            str(repo_path)
        ]
        
        self._run_command(cmd, cwd=self.projects_dir)
        logger.info(f"Successfully cloned {project.name}")
    
    def _pull_repo(self, repo_path: Path, project: ProjectConfig) -> None:
        """Pull latest changes from remote."""
        cmd = ["git", "pull", "--ff-only"]
        
        try:
            self._run_command(cmd, cwd=repo_path)
            logger.info(f"Successfully pulled {project.name}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Pull failed for {project.name}: {e.stderr}")
    
    def _init_submodules(self, repo_path: Path, project: ProjectConfig) -> None:
        """Initialize and update submodules."""
        # Step 1: Rewrite .gitmodules if needed (SSH -> HTTPS with token)
        gitmodules_path = repo_path / ".gitmodules"
        if gitmodules_path.exists() and project.github_token:
            content = gitmodules_path.read_text()
            
            # Replace SSH with HTTPS + token
            content = content.replace(
                "git@github.com:",
                f"https://x-access-token:{project.github_token}@github.com/"
            )
            
            gitmodules_path.write_text(content)
            logger.info(f"Rewrote .gitmodules for {project.name}")
        
        # Step 2: Sync submodule URLs
        cmd = ["git", "submodule", "sync", "--recursive"]
        self._run_command(cmd, cwd=repo_path)
        
        # Step 3: Initialize and update submodules
        cmd = [
            "git", "submodule", "update",
            "--init", "--recursive", "--depth", "1"
        ]
        self._run_command(cmd, cwd=repo_path)
        logger.info(f"Successfully initialized submodules for {project.name}")
    
    def _update_submodules(self, repo_path: Path, project: ProjectConfig) -> None:
        """Update existing submodules."""
        cmd = [
            "git", "submodule", "update",
            "--recursive", "--remote"
        ]
        
        try:
            self._run_command(cmd, cwd=repo_path)
            logger.info(f"Successfully updated submodules for {project.name}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Submodule update failed for {project.name}: {e.stderr}")
    
    def _get_authenticated_url(self, url: str, token: Optional[str]) -> str:
        """Add authentication token to HTTPS URL if provided."""
        if not token or not url.startswith("https://"):
            return url
        
        return url.replace("https://", f"https://x-access-token:{token}@")
    
    def _run_command(self, cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True
        )
        return result
