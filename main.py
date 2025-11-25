from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from datetime import datetime

app = FastAPI()

# ============================
#  CONFIG SUPABASE
# ============================
SUPABASE_URL = os.getenv("SUPABASE_URL")           # ex: https://sdtjpntumeadkghfmsmo.supabase.co
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service_role key

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY doivent être définies dans Render.")

USERS_TABLE_URL = f"{SUPABASE_URL}/rest/v1/users"


def supabase_headers(prefer_return: str = "return=minimal"):
    """Headers pour appeler l'API REST Supabase."""
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer_return,
    }


# ============================
#  MODELES Pydantic
# ============================

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


# ============================
#  HELPERS SUPABASE
# ============================

async def get_user(user_id: str):
    """Récupère un utilisateur par userId."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={"userId": f"eq.{user_id}", "select": "*"},
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase error: {resp.text}")

    data = resp.json()
    if not data:
        return None
    return data[0]


async def patch_user(user_id: str, fields: dict):
    """PATCH sur un utilisateur donné."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            USERS_TABLE_URL,
            params={"userId": f"eq.{user_id}"},
            json=fields,
            headers=supabase_headers(prefer_return="return=minimal"),
            timeout=10.0,
        )
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=f"Supabase patch error: {resp.text}")


# ============================
#  ROUTES
# ============================

@app.post("/initUser")
async def init_user(payload: UserInit):
    """
    Crée un user si inexistant.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            USERS_TABLE_URL,
            params={"on_conflict": "userId"},
            json={
                "userId": payload.userId,
                "username": payload.username,
            },
            headers=supabase_headers(prefer_return="resolution=merge-duplicates"),
            timeout=10.0,
        )
    if resp.status_code not in (200, 201, 204):
        raise HTTPException(status_code=500, detail=f"Supabase initUser error: {resp.text}")
    return {"ok": True}


@app.post("/addScore")
async def add_score(payload: ScoreUpdate):
    user = await get_user(payload.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    score_global = (user.get("score_global") or 0) + payload.score
    score_weekly = (user.get("score_weekly") or 0) + payload.score
    now_iso = datetime.utcnow().isoformat()

    await patch_user(
        payload.userId,
        {
            "score_global": score_global,
            "score_weekly": score_weekly,
            "lastactivedate": now_iso,
        },
    )
    return {"ok": True}


@app.post("/roundsPlayed")
async def rounds_played(payload: dict):
    user_id = payload.get("userId")
    rounds = payload.get("rounds")

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing userId")
    if rounds is None:
        raise HTTPException(status_code=400, detail="Missing rounds")

    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_rounds = user.get("roundsPlayed") or 0
    new_total = current_rounds + rounds

    await patch_user(
        user_id,
        {"roundsPlayed": new_total}
    )

    return {"ok": True, "newRoundsPlayed": new_total}



@app.post("/gamePlayed")
async def game_played(payload: StatUpdate):
    user = await get_user(payload.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    games = (user.get("gamesPlayed") or 0) + 1
    await patch_user(payload.userId, {"gamesPlayed": games})
    return {"ok": True}


@app.get("/leaderboard/global")
async def leaderboard_global():
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={
                "select": "username,score_global",
                "order": "score_global.desc",
                "limit": "50",
            },
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase leaderboard error: {resp.text}")
    return resp.json()


@app.get("/leaderboard/weekly")
async def leaderboard_weekly():
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={
                "select": "username,score_weekly",
                "order": "score_weekly.desc",
                "limit": "50",
            },
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase leaderboard weekly error: {resp.text}")
    return resp.json()


@app.post("/purchase/pack")
async def purchase_pack(payload: PackPurchase):
    user = await get_user(payload.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.productId == "pytha.pack10":
        amount = 10 * payload.quantity
    elif payload.productId == "pytha.pack20":
        amount = 20 * payload.quantity
    else:
        amount = 0

    remaining = (user.get("remainingPlays") or 0) + amount
    await patch_user(payload.userId, {"remainingPlays": remaining})
    return {"ok": True, "remainingPlays": remaining}


@app.post("/consumePlay")
async def consume_play(payload: StatUpdate):
    user = await get_user(payload.userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    remaining = user.get("remainingPlays") or 0
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="No remaining plays")

    remaining -= 1
    await patch_user(payload.userId, {"remainingPlays": remaining})
    return {"ok": True, "remainingPlays": remaining}


@app.post("/subscription/update")
async def subscription(payload: SubscriptionUpdate):
    await patch_user(
        payload.userId,
        {
            "originalTransactionId": payload.originalTransactionId,
            "subscriptionStatus": payload.isActive,
        },
    )
    return {"ok": True}


@app.post("/resetWeekly")
async def reset_weekly():
    """
    Remet score_weekly à 0 pour tous les users.
    Nécessite la service_role key et des policies RLS adaptées.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            USERS_TABLE_URL,
            params={},  # pas de filtre => tous les users
            json={"score_weekly": 0},
            headers=supabase_headers(prefer_return="return=minimal"),
            timeout=20.0,
        )
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=f"Supabase resetWeekly error: {resp.text}")
    return {"ok": True}


@app.get("/testdb")
async def test_db():
    """
    Test simple : essaie de lire 1 user depuis Supabase.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={"select": "*", "limit": "1"},
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase test error: {resp.text}")
    return resp.json()


@app.get("/")
def root():
    return {"message": "Pytha API running 🎉 (Supabase REST mode)"}

@app.get("/getUser")
async def get_user_data(userId: str):
    """
    Renvoie toutes les données utilisateur (pour synchroniser GameState).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={"userId": f"eq.{userId}", "select": "*"},
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase getUser error: {resp.text}")

    data = resp.json()
    if not data:
        return {"exists": False}

    return {
        "exists": True,
        "user": data[0]
    }

@app.post("/updateUser")
async def update_user(payload: dict):
    user_id = payload.get("userId")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing userId")

    # remove userId from fields we patch
    fields = {k: v for k, v in payload.items() if k != "userId"}

    if not fields:
        return {"ok": True}

    await patch_user(user_id, fields)
    return {"ok": True}

@app.get("/checkUsername")
async def check_username(username: str):
    """
    Vérifie si un username est disponible.
    Retourne: { "available": true/false }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            USERS_TABLE_URL,
            params={"username": f"eq.{username}", "select": "username"},
            headers=supabase_headers(prefer_return="return=representation"),
            timeout=10.0
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Supabase error: {resp.text}")

    data = resp.json()
    return {"available": len(data) == 0}
@app.post("/resetUser")
async def reset_user(data: dict):

    user_id = data.get("userId")
    username = data.get("username")
    last_active = data.get("lastactivedate")
    reset_sub = data.get("resetSubscriptionData", False)

    if not user_id:
        raise HTTPException(status_code=400, detail="Missing userId")

    reset_values = {
        "username": "",
        "score_global": 0,
        "score_weekly": 0,
        "gamesPlayed": 0,
        "roundsPlayed": 0,
        "remainingPlays": 0,
        "lastactivedate": last_active,
    }

    if reset_sub:
        reset_values["subscriptionStatus"] = False
        reset_values["originalTransactionId"] = None

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            USERS_TABLE_URL,
            params={"userId": f"eq.{user_id}"},
            json=reset_values,
            headers=supabase_headers(prefer_return="return=minimal"),
            timeout=10.0,
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=500, detail=f"Supabase resetUser error: {resp.text}")

    return {"ok": True}
