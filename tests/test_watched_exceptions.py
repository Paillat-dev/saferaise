"""Tests for _watched_exceptions.py (sync)."""

import pytest

from saferaise import disable, enable, unsafe
from saferaise._errors import NotEnteredError
from saferaise._watched_exceptions import get_exceptions, watch_exceptions


class TestGetExceptions:
    def test_default_is_none(self):
        assert get_exceptions() is None


class TestEnable:
    def test_sets_empty_frozenset(self):
        with enable():
            assert get_exceptions() == frozenset()

    def test_restores_on_exit(self):
        with enable():
            pass
        assert get_exceptions() is None

    def test_nested_enable(self):
        with enable():
            with enable():
                assert get_exceptions() == frozenset()
            assert get_exceptions() == frozenset()


class TestWatchExceptions:
    def test_adds_to_set(self):
        with enable():
            with watch_exceptions(ValueError):
                assert ValueError in (get_exceptions() or frozenset())

    def test_stacks_correctly(self):
        with enable():
            with watch_exceptions(ValueError):
                with watch_exceptions(TypeError):
                    current = get_exceptions()

                    assert current is not None

                    assert ValueError in current
                    assert TypeError in current

                assert ValueError in (get_exceptions() or frozenset())
                assert TypeError not in (get_exceptions() or frozenset())

    def test_restores_on_exit(self):
        with enable():
            with watch_exceptions(ValueError):
                pass
            assert get_exceptions() == frozenset()

    def test_multiple_types(self):
        with enable():
            with watch_exceptions(ValueError, TypeError):
                current = get_exceptions()

                assert current is not None

                assert ValueError in current
                assert TypeError in current

    def test_deduplication(self):
        with enable():
            with watch_exceptions(ValueError):
                with watch_exceptions(ValueError):
                    current = get_exceptions()
                    assert current == frozenset({ValueError})

    def test_exit_without_enter_raises(self):
        ctx = watch_exceptions(ValueError)
        with pytest.raises(NotEnteredError):
            ctx.__exit__(None, None, None)

    def test_not_enabled_stays_none(self):
        with watch_exceptions(ValueError):
            assert get_exceptions() is None


class TestDisable:
    def test_sets_none_inside_enable(self):
        with enable():
            with disable():
                assert get_exceptions() is None

    def test_restores_on_exit(self):
        with enable():
            with watch_exceptions(ValueError):
                with disable():
                    pass
                assert ValueError in (get_exceptions() or frozenset())


class TestUnsafe:
    def test_adds_exceptions(self):
        with enable():
            with unsafe(ValueError):
                assert ValueError in (get_exceptions() or frozenset())

    def test_restores_on_exit(self):
        with enable():
            with unsafe(ValueError):
                pass
            assert get_exceptions() == frozenset()

    def test_when_not_enabled_stays_none(self):
        with unsafe(ValueError):
            assert get_exceptions() is None
