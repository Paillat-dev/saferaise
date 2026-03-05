"""Async tests for _watched_exceptions.py."""

import asyncio

from saferaise import enable, unsafe
from saferaise._watched_exceptions import get_exceptions, watch_exceptions


class TestAsyncEnable:
    async def test_enable_in_async(self):
        with enable():
            assert get_exceptions() == frozenset()

    async def test_watch_exceptions_in_async(self):
        with enable():
            with watch_exceptions(ValueError):
                assert ValueError in (get_exceptions() or frozenset())

    async def test_unsafe_in_async(self):
        with enable():
            with unsafe(ValueError):
                assert ValueError in (get_exceptions() or frozenset())


class TestAsyncContextVarIsolation:
    async def test_concurrent_tasks_isolated(self):
        results = {}

        async def task_a():
            with enable():
                with unsafe(ValueError):
                    await asyncio.sleep(0.01)
                    results["a"] = get_exceptions()

        async def task_b():
            with enable():
                with unsafe(TypeError):
                    await asyncio.sleep(0.01)
                    results["b"] = get_exceptions()

        await asyncio.gather(task_a(), task_b())

        assert ValueError in results["a"]
        assert TypeError not in results["a"]
        assert TypeError in results["b"]
        assert ValueError not in results["b"]

    async def test_task_does_not_affect_parent(self):
        with enable():
            with unsafe(ValueError):

                async def child():
                    with unsafe(TypeError):
                        await asyncio.sleep(0)

                await asyncio.create_task(child())
                current = get_exceptions()

                assert current is not None

                assert ValueError in current
                assert TypeError not in current
