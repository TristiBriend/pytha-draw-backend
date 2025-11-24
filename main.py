from fastapi import FastAPI
from pydantic import BaseModel
import asyncpg
import os
from datetime import datetime

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

class UserInit(BaseModel):
    userId: str
    username: str

class ScoreUpdate(BaseModel):
    userId: str
    score: int

class StatUpdate(BaseModel):
    userId: str

class PackPurchase(BaseModel):
    userId: str
    productId: str
    quantity: int

class SubscriptionUpdate(BaseModel):
    userId: str
    originalTransactionId: str
    isActive: bool

@app.post("/initUser")
async def init_user(payload: UserInit):
    conn = await get_db()
    await conn.execute("""
        INSERT INTO users (userId, username)
        VALUES (, )
        ON CONFLICT (userId) DO NOTHING;
    """, payload.userId, payload.username)
    await conn.close()
    return {"ok": True}

@app.post("/addScore")
async def add_score(payload: ScoreUpdate):
    conn = await get_db()
    await conn.execute("""
        UPDATE users
        SET score_global = score_global + ,
            score_weekly = score_weekly + ,
            lastActiveDate = now()
        WHERE userId = ;
    """, payload.score, payload.userId)
    await conn.close()
    return {"ok": True}

@app.post("/roundPlayed")
async def round_played(payload: StatUpdate):
    conn = await get_db()
    await conn.execute("""
        UPDATE users SET roundsPlayed = roundsPlayed + 1
        WHERE userId = ;
    """, payload.userId)
    await conn.close()
    return {"ok": True}

@app.post("/gamePlayed")
async def game_played(payload: StatUpdate):
    conn = await get_db()
    await conn.execute("""
        UPDATE users SET gamesPlayed = gamesPlayed + 1
        WHERE userId = ;
    """, payload.userId)
    await conn.close()
    return {"ok": True}

@app.get("/leaderboard/global")
async def leaderboard_global():
    conn = await get_db()
    rows = await conn.fetch("""
        SELECT username, score_global
        FROM users
        ORDER BY score_global DESC
        LIMIT 50;
    """)
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/leaderboard/weekly")
async def leaderboard_weekly():
    conn = await get_db()
    rows = await conn.fetch("""
        SELECT username, score_weekly
        FROM users
        ORDER BY score_weekly DESC
        LIMIT 50;
    """)
    await conn.close()
    return [dict(r) for r in rows]

@app.post("/purchase/pack")
async def purchase_pack(payload: PackPurchase):
    conn = await get_db()

    if payload.productId == "pytha.pack10":
        amount = 10 * payload.quantity
    elif payload.productId == "pytha.pack20":
        amount = 20 * payload.quantity
    else:
        amount = 0

    await conn.execute("""
        UPDATE users
        SET remainingPlays = remainingPlays + 
        WHERE userId = ;
    """, amount, payload.userId)
    await conn.close()
    return {"ok": True}

@app.post("/consumePlay")
async def consume_play(payload: StatUpdate):
    conn = await get_db()
    await conn.execute("""
        UPDATE users
        SET remainingPlays = remainingPlays - 1
        WHERE userId =  AND remainingPlays > 0;
    """, payload.userId)
    await conn.close()
    return {"ok": True}

@app.post("/subscription/update")
async def subscription(payload: SubscriptionUpdate):
    conn = await get_db()
    await conn.execute("""
        UPDATE users
        SET originalTransactionId = ,
            subscriptionStatus = 
        WHERE userId = ;
    """, payload.originalTransactionId, payload.isActive, payload.userId)
    await conn.close()
    return {"ok": True}

@app.post("/resetWeekly")
async def reset_weekly():
    conn = await get_db()
    await conn.execute("UPDATE users SET score_weekly = 0;")
    await conn.close()
    return {"ok": True}

@app.get("/testdb")
async def test_db():
    conn = await get_db()
    rows = await conn.fetch("SELECT * FROM users LIMIT 1;")
    await conn.close()
    return [dict(r) for r in rows]

@app.get("/")
def root():
    return {"message": "Pytha API running 🎉"}
