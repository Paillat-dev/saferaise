"""End-to-end integration tests."""

import asyncio

import pytest

from saferaise import disable, enable, unsafe
from saferaise._decorator import raises
from saferaise._errors import UnwatchedRaiseError
from saferaise._watched_exceptions import get_exceptions

from .conftest import AnotherError, ChildError, CustomError


class TestSyncIntegration:
    def test_enable_unsafe_raises_succeeds(self):
        with enable():
            with unsafe(CustomError):

                @raises(CustomError)
                def fn():
                    return "ok"

                assert fn() == "ok"

    def test_enable_raises_unwatched(self):
        with enable():

            @raises(CustomError)
            def fn():
                return "ok"

            with pytest.raises(UnwatchedRaiseError):
                fn()

    def test_enable_disable_bypasses(self):
        with enable():
            with disable():

                @raises(CustomError)
                def fn():
                    return "ok"

                assert fn() == "ok"

    def test_exception_raised_and_caught(self):
        with enable():
            with unsafe(CustomError):

                @raises(CustomError)
                def fn():
                    raise CustomError("test")

                with pytest.raises(CustomError, match="test"):
                    fn()

    def test_deeply_nested_chain(self):
        with enable():
            with unsafe(CustomError, AnotherError, ChildError):

                @raises(CustomError)
                def level1():
                    return level2()

                @raises(AnotherError)
                def level2():
                    return level3()

                @raises(ChildError)
                def level3():
                    return "deep"

                assert level1() == "deep"

    def test_watch_set_restored_after_call(self):
        with enable():
            before = get_exceptions()

            with unsafe(CustomError):

                @raises(CustomError)
                def fn():
                    return get_exceptions()

                during = fn()

            after = get_exceptions()

            assert before is not None
            assert after is not None
            assert during is not None

            assert CustomError in during
            assert CustomError not in before
            assert CustomError not in after
            assert before == after


class TestAsyncIntegration:
    async def test_enable_unsafe_raises_succeeds(self):
        with enable():
            with unsafe(CustomError):

                @raises(CustomError)
                async def fn():
                    return "ok"

                assert await fn() == "ok"

    async def test_enable_raises_unwatched(self):
        with enable():

            @raises(CustomError)
            async def fn():
                return "ok"

            with pytest.raises(UnwatchedRaiseError):
                await fn()

    async def test_enable_disable_bypasses(self):
        with enable():
            with disable():

                @raises(CustomError)
                async def fn():
                    return "ok"

                assert await fn() == "ok"

    async def test_concurrent_tasks_isolated(self):
        results = {}

        @raises(CustomError)
        async def task_custom():
            await asyncio.sleep(0.01)
            results["custom"] = get_exceptions()
            return "custom"

        @raises(AnotherError)
        async def task_another():
            await asyncio.sleep(0.01)
            results["another"] = get_exceptions()
            return "another"

        async def run_custom():
            with enable():
                with unsafe(CustomError):
                    return await task_custom()

        async def run_another():
            with enable():
                with unsafe(AnotherError):
                    return await task_another()

        r1, r2 = await asyncio.gather(run_custom(), run_another())
        assert r1 == "custom"
        assert r2 == "another"
        assert CustomError in results["custom"]
        assert AnotherError not in results["custom"]
        assert AnotherError in results["another"]
        assert CustomError not in results["another"]

    async def test_deeply_nested_async_chain(self):
        with enable():
            with unsafe(CustomError, AnotherError, ChildError):

                @raises(CustomError)
                async def level1():
                    return await level2()

                @raises(AnotherError)
                async def level2():
                    return await level3()

                @raises(ChildError)
                async def level3():
                    return "deep"

                assert await level1() == "deep"
