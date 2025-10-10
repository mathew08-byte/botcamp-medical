import os
import redis

try:
    import rq
except Exception:
    rq = None


def main() -> int:
    if rq is None:
        print("rq not installed; skipping")
        return 0
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    failed = rq.Queue("failed", connection=r)
    default = rq.Queue("default", connection=r)
    count = 0
    for job in list(failed.jobs):
        failures = int((job.meta or {}).get("failures", 0))
        if failures < 3:
            job.requeue()
            count += 1
    print(f"Requeued {count} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

