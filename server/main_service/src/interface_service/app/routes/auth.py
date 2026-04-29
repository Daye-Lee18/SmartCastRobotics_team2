"""Authentication / Operator lookup — 2026-04-26 작업 3 (로그인 연동).

PyQt 후처리 작업자가 시작 시 이메일을 입력하면 user_account 테이블에서 user_id 와
role 을 찾아 응답한다. 비밀번호는 dev 단계에서 검증 안 함 (CLAUDE.md 의 평문 정책).

엔드포인트:
  POST /api/auth/lookup  body={"email": "..."}  → {user_id, user_nm, role, ...}
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from smart_cast_db.database import get_db
from smart_cast_db.models import UserAccount

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/lookup")
def lookup_user(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
) -> dict:
    """이메일로 사용자 조회 (PyQt 작업자 로그인용).

    Body:
      email : str (required)
    Returns:
      {user_id, co_nm, user_nm, role, email}
    """
    email = (payload.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail=f"user not found: {email}")
    return {
        "user_id": user.user_id,
        "co_nm": user.co_nm,
        "user_nm": user.user_nm,
        "role": user.role,
        "email": user.email,
    }
