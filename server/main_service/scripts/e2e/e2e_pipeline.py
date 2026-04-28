"""E2E 파이프라인 검증 — AWS RDS Casting (public schema)."""
import datetime
import sys

import requests
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv('.env.local')

from app.database import engine

BASE = "http://localhost:8000"
S = requests.Session()

def J(method, path, **kw):
    r = S.request(method, BASE + path, timeout=15, **kw)
    print(f"{method:5s} {path:60s} → {r.status_code}")
    if r.status_code >= 400:
        print(f"        ERROR: {r.text[:300]}")
        return None
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return r.text

def DB(sql, **p):
    with engine.connect() as conn:
        return list(conn.execute(text(sql), p).all())

print("="*82)
print("E2E PIPELINE — AWS RDS Casting (public schema)")
print("="*82)

# PHASE 1: 신규 고객 발주
print("\n[PHASE 1] 고객 발주 — product_id='R-D450' → ptn_loc=1 자동 매핑")
print("-"*82)
res = J("POST", "/api/orders/customer", json={
    "company_name": "광원건설",
    "customer_name": "테스트 발주자",
    "phone": "010-0000-0000",
    "email": "contact@kwangwon.co.kr",
    "shipping_address": "서울시 테스트구",
    "total_amount": 200000.0,
    "requested_delivery": "2026-12-31",
    "details": [{
        "product_id": "R-D450",
        "product_name": "원형맨홀 D450",
        "quantity": 1,
        "diameter": "450mm",
        "thickness": "30mm",
        "load_class": "일반",
        "material": "주철",
        "post_processing_ids": ["polish","coat"],
        "unit_price": 200000.0,
        "subtotal": 200000.0,
    }],
})
if not res:
    sys.exit(1)
ord_id = res["ord_id"]
print(f"  ✔ ord_id={ord_id}")
print(f"  ✔ pattern: {DB('SELECT ptn_id, ptn_loc FROM public.pattern WHERE ptn_id=:p', p=ord_id)}")
print(f"  ✔ ord_pp_map: {DB('SELECT pp_id FROM public.ord_pp_map WHERE ord_id=:p', p=ord_id)}")
print(f"  ✔ ord_stat: {DB('SELECT stat_id, ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id', p=ord_id)}")

# PHASE 2: APPR
print("\n[PHASE 2] 발주 승인 RCVD → APPR")
print("-"*82)
J("POST", f"/api/orders/{ord_id}/status?new_stat=APPR")
print(f"  ✔ ord_stat: {DB('SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id', p=ord_id)}")

# PHASE 3: 라인 투입
print("\n[PHASE 3] 라인 투입 — Item + RA1/MM equip_task_txn 생성")
print("-"*82)
sp = J("POST", "/api/production/start", json={"ord_id": ord_id})
print(f"  → start: {sp}")
items = DB("SELECT item_id, cur_stat, equip_task_type, cur_res FROM public.item WHERE ord_id=:p", p=ord_id)
print(f"  ✔ items: {items}")
if not items:
    sys.exit(1)
item_id = items[0].item_id
print(f"  ✔ equip_task_txn: {DB('SELECT txn_id, task_type, txn_stat, res_id FROM public.equip_task_txn WHERE item_id=:p ORDER BY txn_id', p=item_id)}")

# PHASE 4: equip advance 체인
print("\n[PHASE 4] equip_task advance: MM → POUR → DM → ToPP")
print("-"*82)
def cur_active(item_id):
    rows = DB("""SELECT txn_id, task_type, txn_stat FROM public.equip_task_txn
                 WHERE item_id=:p AND txn_stat IN ('QUE','PROC') ORDER BY txn_id DESC LIMIT 1""", p=item_id)
    return rows[0] if rows else None

handoff_triggered = False
for step in range(1, 50):
    a = cur_active(item_id)
    if not a:
        print(f"  step{step}: 활성 task 없음 → 종료")
        break
    r = J("POST", f"/api/production/equip-tasks/{a.txn_id}/advance")
    if r is None:
        break
    auto = r.get('auto') or {}
    print(f"  step{step:2d}: txn={a.txn_id} {a.task_type:7s} {r.get('prev_stat') or '-':10s} → {r.get('new_stat'):10s} item={r.get('item_cur_stat'):10s} auto={auto}")
    if auto.get('next_trans_txn_id'):
        print(f"     → ToPP trans_task_txn 생성 (id={auto['next_trans_txn_id']}) — Phase 5 진입")
        handoff_triggered = True
        break

print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=item_id)}")
trans = DB("SELECT trans_task_txn_id, task_type, txn_stat, chg_loc_id FROM public.trans_task_txn WHERE item_id=:p", p=item_id)
print(f"  → trans_task_txn: {trans}")

# PHASE 5: handoff
print("\n[PHASE 5] 핸드오프 ACK (ToPP → PP, pp_task_txn QUE 생성)")
print("-"*82)
ho = J("POST", "/api/debug/handoff-ack", json={})
print(f"  → handoff response: {ho}")
print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=item_id)}")
pp_txns = DB("SELECT txn_id, pp_nm, txn_stat FROM public.pp_task_txn WHERE item_id=:p ORDER BY txn_id", p=item_id)
print(f"  → pp_task_txn: {pp_txns}")
print(f"  → handoff_acks 최신: {DB('SELECT id, task_id, zone, ack_source FROM public.handoff_acks ORDER BY id DESC LIMIT 1')}")

# PHASE 6: RFID
print("\n[PHASE 6] RFID 스캔 — rfid_scan_log INSERT")
print("-"*82)
yyyymmdd = datetime.datetime.now().strftime("%Y%m%d")
payload = f"order_{ord_id}_item_{yyyymmdd}_{item_id}"
rfid = J("POST", "/api/debug/sim/rfid-scan", json={
    "reader_id":"PYQT-WORKER","zone":"postprocessing","raw_payload":payload})
print(f"  → matched={rfid.get('matched') if rfid else None} item.item_id={rfid.get('item',{}).get('item_id') if rfid else None}")
print(f"  → rfid_scan_log: {DB('SELECT id, item_id, raw_payload, parse_status FROM public.rfid_scan_log ORDER BY id DESC LIMIT 1')}")

# PHASE 7: TOF1
print("\n[PHASE 7] TOF1 진입 — pp_task_txn SUCC + item PP→ToINSP + ToINSP equip_task PROC")
print("-"*82)
tof1 = J("POST", "/api/debug/sim/conveyor-tof1", json={
    "res_id":"CONV-01","item_id":item_id,"rfid_payload":payload})
print(f"  → tof1 response: {tof1}")
print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=item_id)}")
print(f"  → pp_task_txn: {DB('SELECT txn_id, pp_nm, txn_stat FROM public.pp_task_txn WHERE item_id=:p', p=item_id)}")
toinsp_q = "SELECT txn_id, task_type, txn_stat, res_id FROM public.equip_task_txn WHERE item_id=:p AND task_type='ToINSP'"
print(f"  → ToINSP equip: {DB(toinsp_q, p=item_id)}")

# PHASE 8: TOF2
print("\n[PHASE 8] TOF2 도달 — ToINSP SUCC + item INSP + insp_task_txn PROC")
print("-"*82)
tof2 = J("POST", "/api/debug/sim/conveyor-tof2", json={"res_id":"CONV-01","item_id":item_id})
print(f"  → tof2 response: {tof2}")
print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=item_id)}")
insp = DB("SELECT txn_id, txn_stat, result FROM public.insp_task_txn WHERE item_id=:p", p=item_id)
print(f"  → insp_task_txn: {insp}")

# PHASE 9: 검사 GP
print("\n[PHASE 9] 검사 완료 GP — item INSP→DONE")
print("-"*82)
if insp:
    cinsp = J("POST", f"/api/quality/inspections/{insp[0].txn_id}/result?result=true")
    print(f"  → complete: {cinsp}")
print(f"  → item: {DB('SELECT item_id, cur_stat, cur_res, is_defective FROM public.item WHERE item_id=:p', p=item_id)}")
print(f"  → insp_task_txn 최종: {DB('SELECT txn_stat, result, end_at FROM public.insp_task_txn WHERE item_id=:p', p=item_id)}")

# PHASE 10: 출하
print("\n[PHASE 10] 출하 단계 전이 DONE → SHIP → COMP")
print("-"*82)
for stat in ["DONE","SHIP","COMP"]:
    J("POST", f"/api/orders/{ord_id}/status?new_stat={stat}")
final = DB("SELECT stat_id, ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id", p=ord_id)
print(f"  ✔ 최종 ord_stat 추이: {[s.ord_stat for s in final]}")

print("\n" + "="*82)
print(f"✓ E2E DONE — ord_id={ord_id} item_id={item_id}")
print("="*82)

# 최종 종합
print("\n[FINAL CHECK] 모든 도메인 테이블에서 item_id 추적")
print("-"*82)
for tbl, q in [
    ("ord", "SELECT ord_id, user_id FROM public.ord WHERE ord_id=:p"),
    ("ord_detail", "SELECT ord_id, qty, due_date FROM public.ord_detail WHERE ord_id=:p"),
    ("ord_stat", "SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id"),
    ("ord_pp_map", "SELECT pp_id FROM public.ord_pp_map WHERE ord_id=:p"),
    ("pattern", "SELECT ptn_loc FROM public.pattern WHERE ptn_id=:p"),
    ("item", "SELECT cur_stat, is_defective FROM public.item WHERE item_id=:i"),
    ("equip_task_txn", "SELECT task_type, txn_stat FROM public.equip_task_txn WHERE item_id=:i ORDER BY txn_id"),
    ("trans_task_txn", "SELECT task_type, txn_stat FROM public.trans_task_txn WHERE item_id=:i"),
    ("pp_task_txn", "SELECT pp_nm, txn_stat FROM public.pp_task_txn WHERE item_id=:i"),
    ("insp_task_txn", "SELECT txn_stat, result FROM public.insp_task_txn WHERE item_id=:i"),
    ("rfid_scan_log", "SELECT raw_payload, parse_status FROM public.rfid_scan_log WHERE item_id=:i"),
]:
    rows = DB(q, p=ord_id, i=item_id) if ":i" in q or ":p" in q else DB(q)
    print(f"  {tbl:18s} ({len(rows):2d} rows): {rows[:3]}")
