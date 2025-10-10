import os

def check_env() -> None:
    print("🔍 Checking environment variables...")
    required = [
        "BOT_TOKEN",
        "DATABASE_URL",
        "REDIS_URL",
        "ADMIN_PASSCODE",
        "SUPER_ADMIN_KEY",
    ]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Missing env vars: {', '.join(missing)}")
    print("✅ Environment variables OK.")


def check_postgres() -> None:
    print("🔍 Checking PostgreSQL connection...")
    import psycopg2

    url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    cur.close(); conn.close()
    print("✅ PostgreSQL:", version)


def check_redis() -> None:
    print("🔍 Checking Redis connection...")
    import redis

    r = redis.from_url(os.getenv("REDIS_URL"))
    r.set("botcamp_ping", "pong")
    print("✅ Redis ping:", r.get("botcamp_ping"))


if __name__ == "__main__":
    check_env()
    check_postgres()
    check_redis()
    print("🎯 All systems operational.")

