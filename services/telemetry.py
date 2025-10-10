import os
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
from services.cache import memory_cache
from database.db import get_async_db
from database.models import TelemetrySnapshot, User, QuizSession, Question, SystemLog, EventLog, ErrorLog
from sqlalchemy import select, func


class TelemetryCollector:
    def __init__(self, interval_seconds: int | None = None) -> None:
        self.interval = interval_seconds or int(os.getenv("TELEMETRY_INTERVAL", "600"))
        self._thread = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                snapshot = self._collect()
                # Save snapshot
                async def _save():
                    async for db in get_async_db():
                        row = TelemetrySnapshot(data=snapshot)
                        db.add(row)
                        await db.commit()
                # Fire and forget (best-effort):
                import asyncio
                try:
                    asyncio.run(_save())
                except Exception:
                    pass
            except Exception:
                pass
            self._stop.wait(self.interval)

    def _collect(self) -> Dict[str, Any]:
        stats = memory_cache.stats()
        # Basic metrics via quick sync calls
        users_total = quizzes_today = uploads_today = active_today = 0
        avg_resp = None
        ai_error_rate = 0.0
        failed_jobs = 0
        async def _query():
            nonlocal users_total, quizzes_today, uploads_today, active_today, ai_error_rate, failed_jobs
            async for db in get_async_db():
                users_total = (await db.execute(select(func.count(User.id)))).scalar() or 0
                quizzes_today = (await db.execute(select(func.count(QuizSession.id)))).scalar() or 0
                uploads_today = (await db.execute(select(func.count(Question.id)))).scalar() or 0
                active_today = users_total  # placeholder
                # AI error rate over last 60 minutes
                from datetime import datetime, timedelta
                since = datetime.utcnow() - timedelta(minutes=60)
                total_ai = (await db.execute(
                    select(func.count(EventLog.id)).where(
                        EventLog.timestamp >= since,
                        EventLog.event_type.in_(["ai_call","ai_parse","ai_moderate"])
                    )
                )).scalar() or 0
                ai_errors = (await db.execute(
                    select(func.count(EventLog.id)).where(
                        EventLog.timestamp >= since,
                        EventLog.event_type.in_(["ai_error","ai_parse_error"])
                    )
                )).scalar() or 0
                ai_error_rate = float((ai_errors / total_ai) * 100.0) if total_ai > 0 else 0.0
                # Failed jobs proxy: critical errors in last hour
                failed_jobs = (await db.execute(
                    select(func.count(ErrorLog.id)).where(
                        ErrorLog.timestamp >= since,
                        ErrorLog.severity == 'critical'
                    )
                )).scalar() or 0
        import asyncio
        try:
            asyncio.run(_query())
        except Exception:
            pass
        return {
            "users_total": users_total,
            "active_today": active_today,
            "uploads_today": uploads_today,
            "quiz_sessions_today": quizzes_today,
            "avg_response_time_ms": avg_resp,
            "cache_hit_ratio": stats.get("hit_ratio", 0.0),
            "failed_jobs": failed_jobs,
            "ai_error_rate": ai_error_rate,
            "timestamp": datetime.utcnow().isoformat(),
        }


collector = TelemetryCollector()

def log_event(event_type: str,
              user_id: Optional[int] = None,
              context: Optional[Dict[str, Any]] = None,
              metadata: Optional[Dict[str, Any]] = None,
              severity: str = "info") -> None:
    """Persist a structured event row for analytics and auditing."""
    async def _save():
        async for db in get_async_db():
            ev = EventLog(
                event_type=event_type,
                user_id=user_id,
                context=(context or {}),
                metadata=(metadata or {}),
                severity=severity,
            )
            db.add(ev)
            await db.commit()
    try:
        import asyncio
        asyncio.run(_save())
    except Exception:
        # Best-effort logging; avoid crashing callers
        pass


