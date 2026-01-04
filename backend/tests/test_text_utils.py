"""Tests for text utilities."""
import pytest
from app.utils.text_utils import smart_truncate, estimate_tokens


def test_smart_truncate_no_truncation_needed():
    """Should return original text if under limit."""
    text = "Short text."
    result = smart_truncate(text, 100)
    assert result == text


def test_smart_truncate_preserve_end():
    """Should preserve end and add marker."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    result = smart_truncate(text, 50, preserve="end")
    assert "[...contexto anterior truncado...]" in result
    assert "Fourth sentence" in result


def test_smart_truncate_preserve_start():
    """Should preserve start and add marker."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    result = smart_truncate(text, 50, preserve="start")
    assert "[...contexto posterior truncado...]" in result
    assert "First sentence" in result


def test_smart_truncate_preserve_both():
    """Should preserve both ends."""
    text = "First sentence. " + ("Middle. " * 50) + "Last sentence."
    result = smart_truncate(text, 100, preserve="both")
    assert "First sentence" in result
    assert "Last sentence" in result
    assert "[...contenido medio truncado...]" in result


def test_estimate_tokens():
    """Should roughly estimate tokens."""
    text = "This is a test with approximately twenty tokens here."
    tokens = estimate_tokens(text)
    assert 10 < tokens < 20  # Rough estimate


def test_smart_truncate_edge_cases():
    """Test edge cases."""
    # Empty string
    assert smart_truncate("", 100) == ""
    
    # Single word longer than limit
    long_word = "a" * 100
    result = smart_truncate(long_word, 50)
    assert len(result) <= 100  # Should still truncate
    
    # Text exactly at limit
    text = "a" * 100
    result = smart_truncate(text, 100)
    assert result == text
