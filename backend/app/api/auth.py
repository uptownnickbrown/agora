from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from ..config import get_settings
from ..deps import DB, CurrentUser
from ..services import auth as auth_svc

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str
    password: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MagicIn(BaseModel):
    email: EmailStr


class RedeemIn(BaseModel):
    token: str


@router.post("/register")
async def register(body: RegisterIn, db: DB):
    user = await auth_svc.register(db, body.email, body.display_name, body.password)
    session = await auth_svc._create_session(db, user)
    return {"token": session.token, "user_id": str(user.id)}


@router.post("/login")
async def login(body: LoginIn, db: DB):
    session = await auth_svc.login_password(db, body.email, body.password)
    return {"token": session.token}


@router.post("/magic/request")
async def magic_request(body: MagicIn, db: DB):
    token = await auth_svc.request_magic_link(db, body.email)
    # Dev mode returns the token; production sends an email instead.
    if get_settings().env in ("dev", "test"):
        return {"sent": True, "dev_token": token}
    return {"sent": True}


@router.post("/magic/redeem")
async def magic_redeem(body: RedeemIn, db: DB):
    session = await auth_svc.redeem_magic_link(db, body.token)
    return {"token": session.token}


@router.get("/me")
async def me(user: CurrentUser, db: DB):
    from sqlalchemy import select

    from ..models import Player, World

    players = (
        await db.scalars(select(Player).where(Player.user_id == user.id))
    ).all()
    worlds = []
    for p in players:
        w = await db.get(World, p.world_id)
        worlds.append({"world_id": str(w.id), "merchant": p.merchant_name,
                       "week": w.current_week, "state": w.state})
    return {"user_id": str(user.id), "email": user.email,
            "display_name": user.display_name, "is_instructor": user.is_instructor,
            "is_admin": user.is_platform_admin, "worlds": worlds}
