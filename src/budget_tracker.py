"""Budget tracking for tool calls and token usage."""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage for API calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, prompt: int, completion: int):
        """Add tokens from an API call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


@dataclass
class BudgetTracker:
    """Track budget usage for an investigation."""
    
    # Tool call counts
    tool_calls: Dict[str, int] = field(default_factory=dict)
    
    # Token usage
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    
    # Model information
    model: str = ""
    
    # Timing
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # API call count
    api_calls: int = 0
    
    def record_tool_call(self, tool_name: str):
        """Record a tool call."""
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1
    
    def record_api_call(self, model: str, prompt_tokens: int, completion_tokens: int):
        """Record an API call with token usage."""
        self.api_calls += 1
        self.model = model
        self.token_usage.add(prompt_tokens, completion_tokens)
    
    def finish(self):
        """Mark the investigation as finished."""
        self.end_time = time.time()
    
    def get_duration(self) -> float:
        """Get duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def format_summary(self) -> str:
        """Format a summary of the budget usage."""
        duration = self.get_duration()
        
        lines = []
        lines.append("📊 **Investigation Stats**")
        lines.append(f"⏱️  Duration: {duration:.1f}s")
        lines.append(f"🤖 Model: {self.model}")
        lines.append(f"🔧 API Calls: {self.api_calls}")
        lines.append(f"🎫 Tokens: {self.token_usage.total_tokens:,} "
                    f"({self.token_usage.prompt_tokens:,} prompt + "
                    f"{self.token_usage.completion_tokens:,} completion)")
        
        if self.tool_calls:
            lines.append("🛠️  Tools Used:")
            for tool, count in sorted(self.tool_calls.items(), key=lambda x: -x[1]):
                lines.append(f"   • {tool}: {count}x")
        
        return "\n".join(lines)
    
    def format_slack_footer(self) -> str:
        """Format a compact footer for Slack messages."""
        duration = self.get_duration()
        tool_summary = ", ".join(
            f"{tool}:{count}" 
            for tool, count in sorted(self.tool_calls.items(), key=lambda x: -x[1])[:5]
        )
        
        return (
            f"_⏱️ {duration:.1f}s | 🤖 {self.model} | "
            f"🎫 {self.token_usage.total_tokens:,} tokens | "
            f"🔧 {self.api_calls} API calls | "
            f"🛠️ {tool_summary}_"
        )
