import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from database.db import get_async_db
from sqlalchemy import text


app = FastAPI()


@app.get("/healthz")
async def healthz():
    return JSONResponse({"status": "ok"})


@app.get("/ready")
async def ready():
    # Check DB connectivity
    try:
        async for db in get_async_db():
            await db.execute(text("SELECT 1"))
            break
    except Exception as e:
        return JSONResponse({"status": "db_error", "detail": str(e)}, status_code=503)
    # Optionally check redis connectivity here if desired
    return JSONResponse({"status": "ready"})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)


