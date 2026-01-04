"""Smart text truncation utilities."""


def smart_truncate(
    text: str,
    max_chars: int,
    max_tokens: int | None = None,
    preserve: str = "end"
) -> str:
    """
    Intelligently truncate text preserving meaningful boundaries.
    
    Args:
        text: Text to truncate
        max_chars: Maximum characters
        max_tokens: Optional token limit (more accurate)
        preserve: Which part to preserve if truncating ("start", "end", "both")
    
    Returns:
        Truncated text with ellipsis markers
    """
    if len(text) <= max_chars:
        return text
    
    if preserve == "end":
        truncated = text[-max_chars:]
        first_period = truncated.find(". ")
        if first_period > 0 and first_period < 200:
            truncated = truncated[first_period + 2:]
        return f"[...truncated beginning...]\n{truncated}"
    
    elif preserve == "start":
        truncated = text[:max_chars]
        last_period = truncated.rfind(". ")
        if last_period > max_chars - 200:
            truncated = truncated[:last_period + 1]
        return f"{truncated}\n[...truncated end...]"
    
    elif preserve == "both":
        half = max_chars // 2
        start = text[:half]
        end = text[-half:]
        
        last_period_start = start.rfind(". ")
        if last_period_start > half - 200:
            start = start[:last_period_start + 1]
        
        first_period_end = end.find(". ")
        if first_period_end > 0 and first_period_end < 200:
            end = end[first_period_end + 2:]
        
        return f"{start}\n[...truncated middle...]\n{end}"
    
    return text[:max_chars]


def estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    return len(text) // 4


def truncate_by_tokens(text: str, max_tokens: int) -> str:
    """Truncate by token count (rough estimation)."""
    max_chars = max_tokens * 4
    return smart_truncate(text, max_chars)
