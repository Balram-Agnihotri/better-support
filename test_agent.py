#!/usr/bin/env python3
"""
Standalone test script for BetterSupport agent.

Usage:
  BETTERCODE_LLM_OPENAI_API_KEY=sk-... python test_agent.py

This script tests the agent without Slack integration.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config, Config, ProjectConfig
from src.git_manager import GitManager
from src.indexer import Indexer
from src.tools import Tools, Workspace
from src.agent import Agent
from src.budget_tracker import BudgetTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def trace_callback(kind: str, title: str, detail: str = ""):
    """Print trace information."""
    icon = {
        "search": "🔎",
        "read": "📖",
        "agent": "🧭",
        "symbol": "🔣",
        "workspace": "📝",
        "assistant": "💬",
        "question": "❓",
        "final": "✅",
        "error": "⚠️",
    }.get(kind, "•")
    
    print(f"\n{icon} {title}")
    if detail:
        # Truncate detail for readability
        if len(detail) > 500:
            detail = detail[:500] + "\n... [truncated]"
        print(f"   {detail[:200]}")


def test_agent():
    """Test the agent with a sample question."""
    try:
        # Load config
        logger.info("Loading configuration...")
        config = load_config()
        
        # Get first project from config
        if not config.projects:
            logger.error("No projects configured in config.yaml")
            sys.exit(1)
        
        project_name = list(config.projects.keys())[0]
        project = config.projects[project_name]
        
        logger.info(f"Using project: {project_name}")
        
        # Ensure repository exists
        logger.info("Ensuring repository exists...")
        git_manager = GitManager(config.projects_dir)
        repo_path = git_manager.ensure_repo(project, skip_pull_if_exists=True)
        
        logger.info(f"Repository at: {repo_path}")
        
        # Build index (or use cached)
        logger.info("Building index...")
        indexer = Indexer.get_or_create(repo_path, config.access, force_rebuild=False)
        
        # Initialize tools and workspace
        workspace = Workspace()
        tools = Tools(indexer, workspace)
        
        # Load agent directory
        agent_dir = repo_path / project.agent_dir
        if not agent_dir.exists():
            agent_dir = repo_path
        
        # Initialize agent
        logger.info("Initializing agent...")
        budget_tracker = BudgetTracker()
        agent = Agent(config, tools, workspace, agent_dir, trace_callback, budget_tracker)
        
        # Ask a test question
        print("\n" + "="*60)
        print("BetterSupport Agent Test")
        print("="*60)
        
        question = input("\nEnter your question (or press Enter for default): ").strip()
        
        if not question:
            question = "What is the main purpose of this repository?"
        
        print(f"\nQuestion: {question}\n")
        print("="*60)
        
        # Get answer
        answer = agent.ask(question, agent_name=project.default_agent)
        
        print("\n" + "="*60)
        print("Final Answer")
        print("="*60)
        print(f"\n{answer}\n")
        
        print("="*60)
        print(budget_tracker.format_summary())
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    test_agent()
