{\rtf1\ansi\ansicpg1252\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from fastapi import FastAPI\
from pydantic import BaseModel\
import asyncpg\
import os\
from datetime import datetime\
\
app = FastAPI()\
\
DATABASE_URL = os.getenv("DATABASE_URL")\
\
\
async def get_db():\
    return await asyncpg.connect(DATABASE_URL)\
\
\
class UserInit(BaseModel):\
    userId: str\
    username: str\
\
\
class ScoreUpdate(BaseModel):\
    userId: str\
    score: int\
\
\
class StatUpdate(BaseModel):\
    userId: str\
\
\
class PackPurchase(BaseModel):\
    userId: str\
    productId: str\
    quantity: int\
\
\
class SubscriptionUpdate(BaseModel):\
    userId: str\
    originalTransactionId: str\
    isActive: bool\
\
\
@app.post("/initUser")\
async def init_user(payload: UserInit):\
    conn = await get_db()\
    await conn.execute("""\
        INSERT INTO users (userId, username)\
        VALUES ($1, $2)\
        ON CONFLICT (userId) DO NOTHING;\
    """, payload.userId, payload.username)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/addScore")\
async def add_score(payload: ScoreUpdate):\
    conn = await get_db()\
    await conn.execute("""\
        UPDATE users\
        SET score_global = score_global + $1,\
            score_weekly = score_weekly + $1,\
            lastActiveDate = now()\
        WHERE userId = $2;\
    """, payload.score, payload.userId)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/roundPlayed")\
async def round_played(payload: StatUpdate):\
    conn = await get_db()\
    await conn.execute("""\
        UPDATE users SET roundsPlayed = roundsPlayed + 1\
        WHERE userId = $1;\
    """, payload.userId)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/gamePlayed")\
async def game_played(payload: StatUpdate):\
    conn = await get_db()\
    await conn.execute("""\
        UPDATE users SET gamesPlayed = gamesPlayed + 1\
        WHERE userId = $1;\
    """, payload.userId)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.get("/leaderboard/global")\
async def leaderboard_global():\
    conn = await get_db()\
    rows = await conn.fetch("""\
        SELECT username, score_global\
        FROM users\
        ORDER BY score_global DESC\
        LIMIT 50;\
    """)\
    await conn.close()\
    return [dict(r) for r in rows]\
\
\
@app.get("/leaderboard/weekly")\
async def leaderboard_weekly():\
    conn = await get_db()\
    rows = await conn.fetch("""\
        SELECT username, score_weekly\
        FROM users\
        ORDERORDER BY score_weekly DESC\
        LIMIT 50;\
    """)\
    await conn.close()\
    return [dict(r) for r in rows]\
\
\
@app.post("/purchase/pack")\
async def purchase_pack(payload: PackPurchase):\
    conn = await get_db()\
\
    amount = 0\
    if payload.productId == "pytha.pack10":\
        amount = 10 * payload.quantity\
    elif payload.productId == "pytha.pack20":\
        amount = 20 * payload.quantity\
\
    await conn.execute("""\
        UPDATE users\
        SET remainingPlays = remainingPlays + $1\
        WHERE userId = $2;\
    """, amount, payload.userId)\
\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/consumePlay")\
async def consume_play(payload: StatUpdate):\
    conn = await get_db()\
    await conn.execute("""\
        UPDATE users\
        SET remainingPlays = remainingPlays - 1\
        WHERE userId = $1 AND remainingPlays > 0;\
    """, payload.userId)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/subscription/update")\
async def subscription(payload: SubscriptionUpdate):\
    conn = await get_db()\
    await conn.execute("""\
        UPDATE users\
        SET originalTransactionId = $1,\
            subscriptionStatus = $2\
        WHERE userId = $3;\
    """, payload.originalTransactionId, payload.isActive, payload.userId)\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.post("/resetWeekly")\
async def reset_weekly():\
    conn = await get_db()\
    await conn.execute("UPDATE users SET score_weekly = 0;")\
    await conn.close()\
    return \{"ok": True\}\
\
\
@app.get("/testdb")\
async def test_db():\
    conn = await get_db()\
    rows = await conn.fetch("SELECT * FROM users LIMIT 1;")\
    await conn.close()\
    return [dict(r) for r in rows]\
\
\
@app.get("/")\
def root():\
    return \{"message": "Pytha API running \uc0\u55356 \u57225 "\}\
}