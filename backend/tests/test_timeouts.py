"""Tests for timeout configuration."""
import pytest
from app.config import TimeoutConfig


def test_timeout_config_values():
    """Should have reasonable timeout values."""
    assert TimeoutConfig.HTTP_SHORT < TimeoutConfig.HTTP_MEDIUM
    assert TimeoutConfig.HTTP_MEDIUM < TimeoutConfig.HTTP_LONG
    assert TimeoutConfig.EMBEDDING < TimeoutConfig.TOTAL
    assert TimeoutConfig.REASONING < TimeoutConfig.TOTAL


def test_get_timeout():
    """Should return correct timeout for operation."""
    assert TimeoutConfig.get_timeout('embedding') == TimeoutConfig.EMBEDDING
    assert TimeoutConfig.get_timeout('llm') == TimeoutConfig.LLM
    assert TimeoutConfig.get_timeout('unknown') == TimeoutConfig.HTTP_MEDIUM


def test_timeout_hierarchy():
    """Timeouts should follow logical hierarchy."""
    # Quick operations should be shorter
    assert TimeoutConfig.EMBEDDING < TimeoutConfig.SEARCH
    assert TimeoutConfig.SEARCH < TimeoutConfig.LLM
    
    # HTTP timeouts should be ordered
    assert TimeoutConfig.HTTP_SHORT == 20.0
    assert TimeoutConfig.HTTP_MEDIUM == 30.0
    assert TimeoutConfig.HTTP_LONG == 60.0
    assert TimeoutConfig.HTTP_VERY_LONG == 90.0


def test_all_timeout_operations():
    """All documented operations should return valid timeouts."""
    operations = ['embedding', 'search', 'llm', 'reasoning', 'total', 'short', 'medium', 'long']
    for op in operations:
        timeout = TimeoutConfig.get_timeout(op)
        assert timeout > 0
        assert isinstance(timeout, (int, float))
