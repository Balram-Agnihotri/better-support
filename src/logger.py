"""Logging utilities for BetterSupport agent."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileLogger:
    """Handles formatted logging to timestamped files."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize file logger.
        
        Args:
            log_dir: Directory to store log files (default: logs)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"log-{timestamp}.log"
        
        # Initialize file
        self.log_file.touch()
    
    def log_event(self, category: str, title: str, content: str, level: str = "INFO") -> None:
        """Log an event to file with formatted output.
        
        Args:
            category: Event category (e.g., 'question', 'search', 'read', 'assistant', 'tool', 'error')
            title: Event title
            content: Event content/details
            level: Log level (INFO, DEBUG, ERROR, WARNING)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Format the log entry
        log_entry = f"""
{'='*80}
[{timestamp}] [{level}] {category.upper()}
Title: {title}
{'='*80}
{content}
"""
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write to log file {self.log_file}: {e}")
    
    def log_api_call(self, model: str, prompt_tokens: int, completion_tokens: int, 
                     total_tokens: Optional[int] = None) -> None:
        """Log API call statistics."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        total = total_tokens or (prompt_tokens + completion_tokens)
        
        log_entry = f"""
{'='*80}
[{timestamp}] [INFO] API_CALL
Model: {model}
Prompt Tokens: {prompt_tokens}
Completion Tokens: {completion_tokens}
Total Tokens: {total}
{'='*80}
"""
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write API call to log file {self.log_file}: {e}")
    
    def log_tool_call(self, tool_name: str, args: dict, result: str, 
                     result_length: int) -> None:
        """Log tool execution details."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = f"""
{'='*80}
[{timestamp}] [INFO] TOOL_EXECUTION
Tool: {tool_name}
Arguments: {args}
Result Length: {result_length} chars
Result Preview: {result[:500]}{"..." if result_length > 500 else ""}
{'='*80}
"""
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write tool call to log file {self.log_file}: {e}")
    
    def log_turn(self, turn_num: int, max_turns: int) -> None:
        """Log turn information."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = f"""
{'*'*80}
[{timestamp}] TURN {turn_num}/{max_turns}
{'*'*80}
"""
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write turn to log file {self.log_file}: {e}")
    
    def log_section(self, title: str) -> None:
        """Log a section header."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        log_entry = f"""
{'#'*80}
[{timestamp}] {title}
{'#'*80}
"""
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write section to log file {self.log_file}: {e}")
    
    def get_log_file(self) -> Path:
        """Get the current log file path."""
        return self.log_file


def create_file_logger(log_dir: str = "logs") -> FileLogger:
    """Factory function to create a FileLogger instance."""
    return FileLogger(log_dir)
