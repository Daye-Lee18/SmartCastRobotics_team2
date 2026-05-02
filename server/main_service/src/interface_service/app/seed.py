"""smartcast schema seed — 마스터 데이터만 INSERT (idempotent).

본 파일은 backend/scripts/seed_masters_v2.sql 와 동일 효과를 SQLAlchemy ORM 으로 수행.
lifespan 에서 매 부팅 시 호출되어도 ON CONFLICT 또는 존재 검사로 중복 방지.

신규 schema 에서는 fresh start 정책 (사용자 결정 2026-04-19) — 트랜잭션 데이터 일체 미삽입.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from smart_cast_db.models import (
    Category,
    ChgLocationStat,
    Equip,
    PpOption,
    Res,
    ShipLocationStat,
    StrgLocationStat,
    Trans,
    UserAccount,
    Zone,
)


def seed_database(db: Session) -> None:
    """smartcast schema 마스터 데이터 (idempotent)."""
    _seed_category(db)
    _seed_pp_options(db)
    _seed_zone(db)
    _seed_res(db)
    _seed_equip(db)
    _seed_trans(db)
    _seed_locations(db)
    _seed_user_admin(db)
    db.commit()


def _seed_category(db: Session) -> None:
    rows = [
        ("CMH", "원형맨홀"),
        ("RMH", "사각맨홀"),
        ("EMH", "타원맨홀"),
    ]
    for cd, nm in rows:
        if not db.get(Category, cd):
            db.add(Category(cate_cd=cd, cate_nm=nm))


def _seed_pp_options(db: Session) -> None:
    rows = [
        ("표면연마", 50000),
        ("방청코팅", 80000),
        ("아연도금", 120000),
        ("로고문구삽입", 60000),
    ]
    for nm, cost in rows:
        if not db.query(PpOption).filter(PpOption.pp_nm == nm).first():
            db.add(PpOption(pp_nm=nm, extra_cost=cost))


def _seed_zone(db: Session) -> None:
    for nm in ["CAST", "PP", "INSP", "STRG", "SHIP", "CHG"]:
        if not db.query(Zone).filter(Zone.zone_nm == nm).first():
            db.add(Zone(zone_nm=nm))


def _seed_res(db: Session) -> None:
    rows = [
        ("PAT",   "RA",   "JetCobot 280 CAST"),
        ("MAT",   "RA",   "JetCobot 280 STRG"),
        ("CONV1", "CONV", "ESP32 Conveyor v5 INSP"),
        ("TAT1",  "TAT",  "PinkyPro"),
        ("TAT2",  "TAT",  "PinkyPro"),
        ("TAT3",  "TAT",  "PinkyPro"),
    ]
    for rid, rtype, model in rows:
        if not db.get(Res, rid):
            db.add(Res(res_id=rid, res_type=rtype, model_nm=model))


def _seed_equip(db: Session) -> None:
    db.flush()  # zone/res 가 db 에 보이도록
    by_zone = {z.zone_nm: z.zone_id for z in db.query(Zone).all()}
    rows = [
        ("PAT",   "CAST"),
        ("MAT",   "STRG"),
        ("CONV1", "INSP"),
    ]
    for rid, zname in rows:
        if not db.get(Equip, rid):
            db.add(Equip(res_id=rid, zone_id=by_zone.get(zname)))


def _seed_trans(db: Session) -> None:
    rows = [
        ("TAT1", 1, 30.0),
        ("TAT2", 1, 30.0),
        ("TAT3", 1, 30.0),
    ]
    for rid, slots, kg in rows:
        if not db.get(Trans, rid):
            db.add(Trans(res_id=rid, slot_count=slots, max_load_kg=kg))


def _seed_locations(db: Session) -> None:
    db.flush()
    by_zone = {z.zone_nm: z.zone_id for z in db.query(Zone).all()}

    # CHG 1x3
    if db.query(ChgLocationStat).count() == 0:
        for c in range(1, 4):
            db.add(ChgLocationStat(zone_id=by_zone["CHG"], loc_row=1, loc_col=c, status="empty"))

    # STRG 3x6
    if db.query(StrgLocationStat).count() == 0:
        for r in range(1, 4):
            for c in range(1, 7):
                db.add(
                    StrgLocationStat(zone_id=by_zone["STRG"], loc_row=r, loc_col=c, status="empty")
                )

    # SHIP 1x5
    if db.query(ShipLocationStat).count() == 0:
        for c in range(1, 6):
            db.add(ShipLocationStat(zone_id=by_zone["SHIP"], loc_row=1, loc_col=c, status="empty"))


def _seed_user_admin(db: Session) -> None:
    """기본 admin/operator/fms 계정 — 개발용 (운영 전 hash 적용 필요)."""
    rows = [
        (
            "SmartCast Robotics",
            "관리자",
            "admin",
            "010-0000-0000",
            "admin@smartcast.kr",
            "admin1234",
        ),
        (
            "SmartCast Robotics",
            "운영자",
            "operator",
            "010-0000-0001",
            "operator@smartcast.kr",
            "operator1234",
        ),
        ("SmartCast Robotics", "FMS", "fms", None, "fms@smartcast.kr", "fms1234"),
    ]
    for co, nm, role, phone, email, pw in rows:
        if not db.query(UserAccount).filter(UserAccount.email == email).first():
            db.add(
                UserAccount(co_nm=co, user_nm=nm, role=role, phone=phone, email=email, password=pw)
            )
