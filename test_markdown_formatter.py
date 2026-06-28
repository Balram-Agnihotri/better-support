#!/usr/bin/env python3
"""Test Markdown to Slack formatter."""

from src.slack.markdown_formatter import markdown_to_slack


def test_markdown_to_slack():
    """Test various markdown formats."""
    
    print("Testing Markdown → Slack Formatter")
    print("=" * 60)
    
    # Test headings
    test_cases = [
        ("# Heading 1", "Headings"),
        ("## Heading 2\n### Heading 3", "Multiple headings"),
        ("**Bold text**", "Bold"),
        ("*Italic text*", "Italic"),
        ("_Italic with underscores_", "Italic underscores"),
        ("`inline code`", "Inline code"),
        ("```\ncode block\n```", "Code block"),
        ("1. First item\n2. Second item\n3. Third item", "Ordered list"),
        ("- First item\n- Second item\n- Third item", "Unordered list (dash)"),
        ("* First item\n* Second item", "Unordered list (asterisk)"),
        ("> This is a quote", "Blockquote"),
        ("---", "Horizontal rule"),
        ("**Summary**: This is the summary\n\n**Details**: These are details", "Agent-style response"),
    ]
    
    for markdown, description in test_cases:
        print(f"\n{description}:")
        print(f"Input:  {repr(markdown)}")
        result = markdown_to_slack(markdown)
        print(f"Output: {repr(result)}")
        print(f"Rendered:\n{result}")
        print("-" * 40)
    
    # Test complex agent response
    print("\n\nComplex Agent Response:")
    print("=" * 60)
    
    agent_response = """## Summary

User authentication uses JWT tokens stored in cookies.

## Details

The authentication flow works as follows:

1. User submits credentials to `/api/auth/login`
2. Server validates credentials
3. JWT token is generated and returned
4. Token is stored in HTTP-only cookie

**Key files**:
- `auth.ts:25-45` - Main authentication logic
- `middleware/auth.ts:12-30` - Request validation

**Confidence**: High

### Technical Implementation

The implementation uses:
- `bcrypt` for password hashing
- `jsonwebtoken` for JWT generation
- `cookie-parser` for cookie handling

> **Note**: Tokens expire after 24 hours

---

_⏱️ 12.3s | 🤖 gpt-4-turbo | 🎫 15,234 tokens | 🔧 3 API calls | 🛠️ search:4, read:3_
"""
    
    print("Input:")
    print(agent_response)
    print("\n" + "=" * 60)
    print("Slack Output:")
    print("=" * 60)
    slack_formatted = markdown_to_slack(agent_response)
    print(slack_formatted)


if __name__ == '__main__':
    test_markdown_to_slack()
