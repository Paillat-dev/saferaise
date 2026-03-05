"""Tests for _decorator.py (sync)."""

import pytest

from saferaise import enable, unsafe
from saferaise._decorator import raises
from saferaise._errors import UnwatchedRaiseError
from saferaise._watched_exceptions import get_exceptions

from .conftest import AnotherError, ChildError, CustomError


class TestNoWatchingActive:
    def test_passes_through(self):
        @raises(ValueError)
        def fn():
            return 42

        assert fn() == 42


class TestMatchingWatch:
    def test_runs_when_watched(self):
        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                def fn():
                    return 99

                assert fn() == 99


class TestUnwatchedRaise:
    def test_raises_unwatched_error(self):
        with enable():

            @raises(ValueError)
            def fn():
                return 1

            with pytest.raises(UnwatchedRaiseError) as exc_info:
                fn()
            assert exc_info.value.missing is ValueError


class TestWatchSetDuringBody:
    def test_adds_exceptions_for_body(self):
        captured = {}

        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                def fn():
                    captured["inside"] = get_exceptions()

                fn()

        assert ValueError in captured["inside"]

    def test_nested_raises(self):
        with enable():
            with unsafe(CustomError):

                @raises(CustomError)
                def outer():
                    @raises(CustomError)
                    def inner():
                        return "ok"

                    return inner()

                assert outer() == "ok"


class TestSubclassBehavior:
    def test_subclass_accepted_when_parent_watched(self):
        with enable():
            with unsafe(CustomError):

                @raises(ChildError)
                def fn():
                    return "ok"

                assert fn() == "ok"

    def test_parent_not_accepted_when_only_child_watched(self):
        with enable():
            with unsafe(ChildError):

                @raises(CustomError)
                def fn():
                    return "ok"

                with pytest.raises(UnwatchedRaiseError):
                    fn()


class TestPreservation:
    def test_preserves_return_value(self):
        @raises(ValueError)
        def fn():
            return {"key": "value"}

        assert fn() == {"key": "value"}

    def test_propagates_raised_exceptions(self):
        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                def fn():
                    raise ValueError("boom")

                with pytest.raises(ValueError, match="boom"):
                    fn()

    def test_preserves_name(self):
        @raises(ValueError)
        def my_function():
            """My docstring."""

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestMultipleExceptions:
    def test_all_must_be_watched(self):
        with enable():
            with unsafe(ValueError):

                @raises(ValueError, TypeError)
                def fn():
                    return 1

                with pytest.raises(UnwatchedRaiseError) as exc_info:
                    fn()
                assert exc_info.value.missing is TypeError

    def test_all_watched_passes(self):
        with enable():
            with unsafe(ValueError, TypeError):

                @raises(ValueError, TypeError)
                def fn():
                    return 1

                assert fn() == 1


class TestEmptyRaises:
    def test_empty_raises_always_passes(self):
        with enable():

            @raises()
            def fn():
                return "ok"

            assert fn() == "ok"


class TestNestedCallChains:
    def test_three_level_chain(self):
        with enable():
            with unsafe(CustomError, AnotherError):

                @raises(CustomError)
                def level1():
                    return level2()

                @raises(AnotherError)
                def level2():
                    return level3()

                @raises(CustomError, AnotherError)
                def level3():
                    return "deep"

                assert level1() == "deep"
