# Async Functions

`saferaise` works with both sync and async functions. The watched set is tracked via `contextvars`, so concurrent async tasks are fully isolated.

## Basic Async Usage

```python
import asyncio
import saferaise

saferaise.register("myapp")

import myapp

async def main():
    with saferaise.enable():
        await myapp.run()

asyncio.run(main())
```

```python
# myapp/client.py
from saferaise import raises

@raises(ConnectionError, TimeoutError)
async def fetch(url: str) -> bytes:
    """Fetch data from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.read()
```

## Concurrent Tasks

Each async task inherits its own copy of the context, so concurrent tasks don't interfere with each other:

```python
# myapp/service.py
from saferaise import raises

@raises(ConnectionError)
async def fetch_user(user_id: int) -> dict:
    ...

@raises(ValueError)
async def parse_config(path: str) -> dict:
    ...

async def main():
    try:
        # These run concurrently - each task has its own watched set
        user, config = await asyncio.gather(
            fetch_user(42),
            parse_config("config.yaml"),
        )
    except ConnectionError:
        print("Failed to fetch user")
    except ValueError:
        print("Invalid config")
```

## Threading

For threads, `enable()` must be called **within each thread**. A parent thread's watched set is not inherited:

```python
import threading
import saferaise

saferaise.register("myapp")
import myapp

def worker():
    with saferaise.enable():  # each thread needs its own enable()
        try:
            myapp.do_work()
        except myapp.WorkError:
            print("Work failed")

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```
