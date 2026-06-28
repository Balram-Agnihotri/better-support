"""Slack event handler."""

import json
import logging
import time
from typing import Dict, Any, Optional, Set

from src.config import Config, load_config
from src.git_manager import GitManager
from src.indexer import Indexer
from src.tools import Tools, Workspace
from src.agent import Agent
from src.budget_tracker import BudgetTracker
from src.slack.verify import verify_signature
from src.slack.responder import SlackResponder

logger = logging.getLogger(__name__)

# In-memory event deduplication
# Format: {event_id: timestamp}
PROCESSED_EVENTS: Dict[str, float] = {}
EVENT_TTL_SECONDS = 3600  # Keep events for 1 hour

def cleanup_old_events():
    """Remove events older than TTL to prevent memory bloat."""
    current_time = time.time()
    expired = [
        event_id for event_id, timestamp in PROCESSED_EVENTS.items()
        if current_time - timestamp > EVENT_TTL_SECONDS
    ]
    for event_id in expired:
        del PROCESSED_EVENTS[event_id]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired events from dedup cache")

def is_duplicate_event(event_id: str) -> bool:
    """Check if event has already been processed."""
    cleanup_old_events()
    
    if event_id in PROCESSED_EVENTS:
        logger.info(f"Duplicate event detected: {event_id}")
        return True
    
    PROCESSED_EVENTS[event_id] = time.time()
    return False


def normalize_event(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize Slack event to a consistent format."""
    event = body.get("event", {})
    event_type = event.get("type")
    
    # Ignore bot messages if configured
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return None
    
    # Ignore message edits/deletes if configured
    if event.get("subtype") in ("message_changed", "message_deleted"):
        return None
    
    # Handle app_mention and message events
    if event_type in ("app_mention", "message"):
        return {
            "type": event_type,
            "channel": event.get("channel"),
            "user": event.get("user"),
            "text": event.get("text", ""),
            "ts": event.get("ts"),
            "thread_ts": event.get("thread_ts"),
        }
    
    return None


def should_process_event(event: Dict[str, Any], config: Config) -> bool:
    """Determine if we should process this event."""
    channel_id = event.get("channel")
    event_type = event.get("type")
    
    if not channel_id:
        return False
    
    # Check if channel is configured
    channel_config = config.channels.get(channel_id)
    if not channel_config:
        return False
    
    # Check triggers
    triggers = channel_config.triggers
    
    if event_type == "app_mention" and triggers.get("appMention", True):
        return True
    
    if event_type == "message" and triggers.get("questionLikeMessages", False):
        # Check if message looks like a question
        text = event.get("text", "").lower()
        if "?" in text or any(text.startswith(q) for q in ["how", "what", "why", "where", "when", "who"]):
            return True
    
    return False


def handle(event: Dict[str, Any], headers: Dict[str, str], body: str) -> Dict[str, Any]:
    """
    Main Slack event handler.
    
    Args:
        event: Parsed event body
        headers: Request headers
        body: Raw request body string
    
    Returns:
        Response dict with statusCode and body
    """
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Configuration error"})
        }
    
    # Verify signature
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_signature(config.slack.signing_secret, timestamp, body, signature):
        logger.warning("Invalid Slack signature")
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "Invalid signature"})
        }
    
    # Handle URL verification challenge
    if event.get("type") == "url_verification":
        return {
            "statusCode": 200,
            "body": json.dumps({"challenge": event.get("challenge")})
        }
    
    # Normalize event
    normalized_event = normalize_event(event)
    if not normalized_event:
        logger.info("Event ignored (bot message or unsupported type)")
        return {"statusCode": 200, "body": json.dumps({"ok": True})}
    
    # Check for duplicate events
    event_id = f"{normalized_event.get('channel')}_{normalized_event.get('ts')}"
    if is_duplicate_event(event_id):
        logger.info(f"Skipping duplicate event: {event_id}")
        return {"statusCode": 200, "body": json.dumps({"ok": True})}
    
    # Check if we should process this event
    if not should_process_event(normalized_event, config):
        logger.info("Event ignored (channel not configured or triggers not met)")
        return {"statusCode": 200, "body": json.dumps({"ok": True})}
    
    # Process event asynchronously (in production, this would be queued)
    try:
        process_question(normalized_event, config)
    except Exception as e:
        logger.error(f"Failed to process question: {e}")
        # Still return 200 to Slack to avoid retries
    
    return {"statusCode": 200, "body": json.dumps({"ok": True})}


def process_question(event: Dict[str, Any], config: Config):
    """Process a question from Slack."""
    channel = event["channel"]
    text = event["text"]
    thread_ts = event.get("thread_ts") or event.get("ts")
    
    # Get channel config
    channel_config = config.channels.get(channel)
    if not channel_config:
        logger.warning(f"No config for channel {channel}")
        return
    
    # Get project config
    project_config = config.projects.get(channel_config.project)
    if not project_config:
        logger.error(f"Project {channel_config.project} not found")
        return
    
    # Initialize Slack responder
    responder = SlackResponder(config.slack.bot_token)
    
    # Post interim message
    interim_msg = None
    if config.slack.post_interim_message:
        interim_response = responder.post_interim_message(channel, thread_ts)
        if interim_response.get("ok"):
            interim_msg = interim_response.get("ts")
    
    try:
        # Ensure repository exists
        git_manager = GitManager(config.projects_dir)
        repo_path = git_manager.ensure_repo(project_config, skip_pull_if_exists=True)
        
        # Build index (or use cached)
        indexer = Indexer.get_or_create(repo_path, config.access, force_rebuild=False)
        
        # Initialize tools and workspace
        workspace = Workspace()
        tools = Tools(indexer, workspace)
        
        # Load agent directory
        agent_dir = repo_path / project_config.agent_dir
        if not agent_dir.exists():
            agent_dir = repo_path  # Fallback to repo root
        
        # Initialize agent with trace callback
        def trace_callback(kind: str, title: str, detail: str = ""):
            logger.info(f"[{kind}] {title}")
            if detail:
                logger.debug(detail[:500])
        
        # Create budget tracker
        budget_tracker = BudgetTracker()
        
        agent = Agent(config, tools, workspace, agent_dir, trace_callback, budget_tracker)
        
        # Ask question
        answer = agent.ask(text, agent_name=channel_config.agent)
        
        # Append budget footer
        footer = "\n\n---\n" + budget_tracker.format_slack_footer()
        final_answer = answer + footer
        
        # Post answer
        if interim_msg and config.slack.response_mode == "thread":
            # Update interim message
            responder.update_message(channel, interim_msg, final_answer)
        else:
            # Post new message
            responder.post_message(channel, final_answer, thread_ts=thread_ts)
    
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        error_msg = f"❌ Sorry, I encountered an error: {str(e)[:200]}"
        
        if interim_msg:
            responder.update_message(channel, interim_msg, error_msg)
        else:
            responder.post_message(channel, error_msg, thread_ts=thread_ts)
