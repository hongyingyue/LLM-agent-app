from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import uuid4
from backend.database import create_user, get_user, verify_password
from backend.types import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(data: RegisterRequest):
    user_id = await create_user(data.username, data.password)
    if not user_id:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "User created successfully"}


@router.post("/login")
async def login(data: LoginRequest):
    user = await get_user(data.username)
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful"}
    