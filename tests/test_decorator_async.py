"""Async tests for _decorator.py."""

import asyncio
import inspect

import pytest

from saferaise import enable, unsafe
from saferaise._decorator import raises
from saferaise._errors import UnwatchedRaiseError
from saferaise._watched_exceptions import get_exceptions

from .conftest import CustomError


class TestAsyncNoWatchingActive:
    async def test_passes_through(self):
        @raises(ValueError)
        async def fn():
            return 42

        assert await fn() == 42


class TestAsyncMatchingWatch:
    async def test_runs_when_watched(self):
        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                async def fn():
                    return 99

                assert await fn() == 99


class TestAsyncUnwatchedRaise:
    async def test_raises_unwatched_error(self):
        with enable():

            @raises(ValueError)
            async def fn():
                return 1

            with pytest.raises(UnwatchedRaiseError) as exc_info:
                await fn()
            assert exc_info.value.missing is ValueError


class TestAsyncWatchSetDuringBody:
    async def test_watch_set_active_during_await(self):
        captured = {}

        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                async def fn():
                    await asyncio.sleep(0)
                    captured["inside"] = get_exceptions()

                await fn()

        assert ValueError in captured["inside"]


class TestAsyncPreservation:
    async def test_preserves_return_value(self):
        @raises(ValueError)
        async def fn():
            return {"key": "value"}

        assert await fn() == {"key": "value"}

    async def test_propagates_raised_exceptions(self):
        with enable():
            with unsafe(ValueError):

                @raises(ValueError)
                async def fn():
                    raise ValueError("boom")

                with pytest.raises(ValueError, match="boom"):
                    await fn()

    async def test_preserves_metadata(self):
        @raises(ValueError)
        async def my_async_function():
            """My async docstring."""

        assert my_async_function.__name__ == "my_async_function"
        assert my_async_function.__doc__ == "My async docstring."


class TestAsyncIsCoroutineFunction:
    def test_async_decorated_is_coroutine_function(self):
        @raises(ValueError)
        async def fn():
            pass

        assert inspect.iscoroutinefunction(fn)

    def test_sync_decorated_is_not_coroutine_function(self):
        @raises(ValueError)
        def fn():
            pass

        assert not inspect.iscoroutinefunction(fn)


class TestAsyncNestedRaises:
    async def test_nested_async_calls(self):
        with enable():
            with unsafe(CustomError, ValueError):

                @raises(CustomError)
                async def outer():
                    return await inner()

                @raises(ValueError)
                async def inner():
                    return "ok"

                assert await outer() == "ok"
