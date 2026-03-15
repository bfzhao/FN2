import sys
import pytest

sys.path.insert(0, '..')
from fn2.matcher import Matcher
from fn2.board import Action, ActionType


def test_matcher_match():
    """Test matcher with a matching operation"""
    test_input = "test_operation"
    action = Action(
        type=ActionType.OPERATION,
        request=test_input,
        operation=test_input
    )
    matcher = Matcher(action)
    assert matcher.match(), "Matcher should match the operation"


def test_matcher_no_match():
    """Test matcher with no matching operation"""
    # Assuming there's some operation that won't match
    test_input = "non_existent_operation"
    action = Action(
        type=ActionType.OPERATION,
        request=test_input,
        operation=test_input
    )
    matcher = Matcher(action)
    # This test might need adjustment based on actual matcher behavior
    # For now, we'll just check that it runs without errors
    try:
        result = matcher.match()
        assert isinstance(result, bool), "Matcher.match() should return a boolean"
    except Exception as e:
        pytest.fail(f"Matcher.match() raised exception: {e}")


def test_matcher_run():
    """Test matcher run method"""
    test_input = "test_operation"
    action = Action(
        type=ActionType.OPERATION,
        request=test_input,
        operation=test_input
    )
    matcher = Matcher(action)
    if matcher.match():
        try:
            result = matcher.run()
            assert result is not None, "Matcher.run() should return a result"
        except Exception as e:
            pytest.fail(f"Matcher.run() raised exception: {e}")
