"""Tests for error handling utilities."""
import pytest
from app.utils.error_handling import GracefulDegradation, degradation


def test_graceful_degradation_initial_state():
    """Initially all features should be enabled."""
    gd = GracefulDegradation()
    assert gd.is_enabled('multi_query')
    assert gd.is_enabled('reranking')
    assert gd.is_enabled('reasoning')


def test_disable_feature():
    """Should disable feature."""
    gd = GracefulDegradation()
    gd.disable_feature('multi_query', 'Test reason')
    assert not gd.is_enabled('multi_query')
    assert gd.is_enabled('reranking')  # Others still enabled


def test_enable_feature():
    """Should re-enable feature."""
    gd = GracefulDegradation()
    gd.disable_feature('multi_query', 'Test')
    assert not gd.is_enabled('multi_query')
    
    gd.enable_feature('multi_query')
    assert gd.is_enabled('multi_query')


def test_multiple_features():
    """Should handle multiple disabled features."""
    gd = GracefulDegradation()
    gd.disable_feature('multi_query', 'Reason 1')
    gd.disable_feature('reranking', 'Reason 2')
    
    assert not gd.is_enabled('multi_query')
    assert not gd.is_enabled('reranking')
    assert gd.is_enabled('reasoning')  # Not disabled


def test_global_degradation_instance():
    """Global instance should be available."""
    assert degradation is not None
    assert isinstance(degradation, GracefulDegradation)
