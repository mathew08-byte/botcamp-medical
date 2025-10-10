#!/usr/bin/env python3
import asyncio
import os
from aiogram import Bot


async def simulate_users(bot: Bot, chat_id: str, n: int = 50) -> None:
    tasks = []
    for i in range(n):
        tasks.append(bot.send_message(chat_id, f"Simulated user {i} starting quiz."))
    await asyncio.gather(*tasks)
    print(f"✅ Simulated {n} users concurrently.")


if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("TEST_CHAT_ID", "")
    if not token or not chat_id:
        raise SystemExit("Set BOT_TOKEN and TEST_CHAT_ID in the environment")
    bot = Bot(token=token)
    asyncio.run(simulate_users(bot, chat_id, n=int(os.getenv("NUM_USERS", "50"))))

