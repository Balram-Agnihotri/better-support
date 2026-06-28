"""Markdown to Slack formatter utility."""

import re


def markdown_to_slack(md: str) -> str:
    """
    Convert Markdown to Slack's formatting syntax.
    
    Works with headings, lists, emphasis, and basic markdown.
    
    Slack formatting:
    - *text* = bold
    - _text_ = italic
    - `code` = code
    
    Args:
        md: Markdown text
    
    Returns:
        Slack-formatted text
    """
    text = md
    
    # First, protect code blocks and inline code from modification
    code_blocks = []
    inline_codes = []
    
    # Extract and protect code blocks
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"___CODE_BLOCK_{len(code_blocks)-1}___"
    text = re.sub(r'```[\s\S]*?```', save_code_block, text)
    
    # Extract and protect inline code
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f"___INLINE_CODE_{len(inline_codes)-1}___"
    text = re.sub(r'`[^`\n]+?`', save_inline_code, text)
    
    # Headings → bold text (# text → *text*)
    # Save these as they're already in bold format
    heading_texts = []
    def save_heading(match):
        heading_texts.append(f"\n*{match.group(1)}*\n")
        return f"___HEADING_{len(heading_texts)-1}___"
    
    text = re.sub(r'^######\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    text = re.sub(r'^#####\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    text = re.sub(r'^####\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.*?)$', save_heading, text, flags=re.MULTILINE)
    
    # Bold: **text** → *text*
    # First, temporarily replace **text** to protect it
    bold_texts = []
    def save_bold(match):
        bold_texts.append(f"*{match.group(1)}*")
        return f"___BOLD_{len(bold_texts)-1}___"
    text = re.sub(r'\*\*([^\*\n]+?)\*\*', save_bold, text)
    
    # Now convert remaining *text* (italic in markdown) → _text_ (italic in Slack)
    text = re.sub(r'\*([^\*\n]+?)\*', r'_\1_', text)
    
    # Restore bold text
    for i, bold_text in enumerate(bold_texts):
        text = text.replace(f"___BOLD_{i}___", bold_text)
    
    # Restore headings
    for i, heading_text in enumerate(heading_texts):
        text = text.replace(f"___HEADING_{i}___", heading_text)
    
    # _text_ is already italic in Slack, keep as-is
    
    # Ordered lists → bullets
    text = re.sub(r'^\d+\.\s+', '• ', text, flags=re.MULTILINE)
    
    # Unordered lists with - → bullets
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    
    # Unordered lists with * → bullets (be careful not to match bold)
    text = re.sub(r'^\*\s+', '• ', text, flags=re.MULTILINE)
    
    # Blockquotes (> text)
    text = re.sub(r'^>\s+', '▌ ', text, flags=re.MULTILINE)
    
    # Horizontal rules → divider line
    text = re.sub(r'^---+$', '──────────', text, flags=re.MULTILINE)
    
    # Restore code blocks
    for i, code_block in enumerate(code_blocks):
        text = text.replace(f"___CODE_BLOCK_{i}___", code_block)
    
    # Restore inline code
    for i, inline_code in enumerate(inline_codes):
        text = text.replace(f"___INLINE_CODE_{i}___", inline_code)
    
    # Remove excessive empty lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()
