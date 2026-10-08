"""
Authentication endpoints for the High School Management System API
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, Any

from ..database import sessions_collection, teachers_collection, verify_password

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


class LoginCredentials(BaseModel):
    username: str
    password: str


def require_teacher(request: Request) -> Dict[str, Any]:
    """Authenticate using the server-issued, expiring login cookie."""
    token = request.cookies.get("teacher_session")
    session = sessions_collection.find_one({
        "_id": sha256(token.encode()).hexdigest(),
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    }) if token else None
    teacher = teachers_collection.find_one({"_id": session["username"]}) if session else None
    if not teacher:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return teacher


@router.post("/login")
def login(credentials: LoginCredentials, request: Request, response: Response) -> Dict[str, Any]:
    """Login a teacher account"""
    # Find the teacher in the database
    teacher = teachers_collection.find_one({"_id": credentials.username})

    # Verify password using Argon2 verifier from database.py
    if not teacher or not verify_password(teacher.get("password", ""), credentials.password):
        raise HTTPException(
            status_code=401, detail="Invalid username or password")

    old_token = request.cookies.get("teacher_session")
    if old_token:
        sessions_collection.delete_one({"_id": sha256(old_token.encode()).hexdigest()})
    token = token_urlsafe(32)
    sessions_collection.insert_one({
        "_id": sha256(token.encode()).hexdigest(),
        "username": teacher["_id"],
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=8)
    })
    response.set_cookie(
        "teacher_session", token, max_age=8 * 60 * 60,
        httponly=True, secure=request.url.scheme == "https", samesite="strict"
    )
    response.headers["Cache-Control"] = "no-store"
    # Return teacher information (excluding password)
    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"]
    }


@router.get("/check-session")
def check_session(response: Response, teacher: Dict[str, Any] = Depends(require_teacher)) -> Dict[str, Any]:
    """Check the signed-in teacher's session."""
    response.headers["Cache-Control"] = "no-store"
    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"]
    }


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    token = request.cookies.get("teacher_session")
    if token:
        sessions_collection.delete_one({"_id": sha256(token.encode()).hexdigest()})
    response.delete_cookie("teacher_session")
