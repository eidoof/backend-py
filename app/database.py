import logging

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL, MONGO_PORT


class DB:
    client: AsyncIOMotorClient = None


db = DB()


async def db_get() -> AsyncIOMotorClient:
    return db.client


async def db_connect():
    db.client = AsyncIOMotorClient(MONGO_URL, MONGO_PORT)


async def db_disconnect():
    db.client.close()
