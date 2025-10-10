import concurrent.futures
import os
import time
from typing import Callable, Any, Dict


class AsyncJobExecutor:
    def __init__(self, max_workers: int | None = None) -> None:
        workers = max_workers or int(os.getenv("ASYNC_THREADS", "5"))
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

    def submit(self, fn: Callable[..., Any], *args, **kwargs) -> concurrent.futures.Future:
        return self._pool.submit(fn, *args, **kwargs)

    def shutdown(self, wait: bool = False) -> None:
        self._pool.shutdown(wait=wait)


def retry_with_backoff(fn: Callable[..., Any], attempts: int = 3, base_delay: float = 1.0, *args, **kwargs) -> Any:
    last_exc = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
    if last_exc:
        raise last_exc


# Global executor
executor = AsyncJobExecutor()


