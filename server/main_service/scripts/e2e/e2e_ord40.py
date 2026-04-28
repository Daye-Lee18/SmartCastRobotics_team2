"""ord_40 e2e — 접수부터 출하 완료까지 풀 사이클."""
import datetime
import sys

import requests
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv('.env.local')

from app.database import engine

BASE = "http://localhost:8000"
ORD_ID = 40
S = requests.Session()

def J(method, path, **kw):
    r = S.request(method, BASE + path, timeout=15, **kw)
    print(f"  {method:5s} {path:55s} → {r.status_code}")
    if r.status_code >= 400:
        print(f"      ERROR: {r.text[:200]}")
        return None
    return r.json()

def DB(sql, **p):
    with engine.connect() as conn:
        return list(conn.execute(text(sql), p).all())

print("="*82)
print(f"ord_id={ORD_ID} 풀 라이프사이클 e2e")
print("="*82)

# 초기 상태
print("\n[INIT] ord_40 상태 확인")
ord_row = DB("SELECT ord_id, user_id, created_at FROM public.ord WHERE ord_id=:p", p=ORD_ID)
print(f"  ord: {ord_row}")
print(f"  ord_stat: {DB('SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id', p=ORD_ID)}")
print(f"  pattern: {DB('SELECT ptn_id, ptn_loc FROM public.pattern WHERE ptn_id=:p', p=ORD_ID)}")
print(f"  ord_pp_map: {DB('SELECT pp_id FROM public.ord_pp_map WHERE ord_id=:p', p=ORD_ID)}")

# PHASE 2: APPR
print("\n[2] 발주 승인 RCVD → APPR")
J("POST", f"/api/orders/{ORD_ID}/status?new_stat=APPR")
print(f"  ord_stat: {[s.ord_stat for s in DB('SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id', p=ORD_ID)]}")

# PHASE 3: 라인 투입
print("\n[3] 라인 투입 (RA1/MM)")
sp = J("POST", "/api/production/start", json={"ord_id": ORD_ID})
print(f"  start: {sp}")
items = DB("SELECT item_id, cur_stat FROM public.item WHERE ord_id=:p", p=ORD_ID)
if not items:
    sys.exit(1)
ITEM_ID = items[0].item_id
print(f"  → item_id={ITEM_ID}")

# PHASE 4: equip advance 체인
print("\n[4] equip_task advance: MM → POUR → DM → ToPP")
def cur_active():
    rows = DB("""SELECT txn_id, task_type, txn_stat FROM public.equip_task_txn
                 WHERE item_id=:p AND txn_stat IN ('QUE','PROC') ORDER BY txn_id DESC LIMIT 1""", p=ITEM_ID)
    return rows[0] if rows else None

for step in range(1, 50):
    a = cur_active()
    if not a:
        break
    r = J("POST", f"/api/production/equip-tasks/{a.txn_id}/advance")
    if not r:
        break
    auto = r.get('auto') or {}
    print(f"  s{step:2d}: txn={a.txn_id} {a.task_type:7s} {r.get('prev_stat') or '-':10s}→{r.get('new_stat'):10s} item={r.get('item_cur_stat')} auto={auto if auto else ''}")
    if auto.get('next_trans_txn_id'):
        break

print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=ITEM_ID)}")

# PHASE 5: handoff
print("\n[5] 핸드오프 ACK")
ho = J("POST", "/api/debug/handoff-ack", json={})
print(f"  → released={ho.get('released') if ho else None} item_id={ho.get('item_id') if ho else None}")
print(f"  → item: {DB('SELECT cur_stat, equip_task_type FROM public.item WHERE item_id=:p', p=ITEM_ID)}")
print(f"  → pp_task_txn: {DB('SELECT pp_nm, txn_stat FROM public.pp_task_txn WHERE item_id=:p', p=ITEM_ID)}")

# PHASE 6: RFID
print("\n[6] RFID 스캔")
yyyymmdd = datetime.datetime.now().strftime("%Y%m%d")
payload = f"order_{ORD_ID}_item_{yyyymmdd}_{ITEM_ID}"
rfid = J("POST", "/api/debug/sim/rfid-scan", json={
    "reader_id":"PYQT-WORKER","zone":"postprocessing","raw_payload":payload})
print(f"  → matched={rfid.get('matched')} item_id={rfid.get('item',{}).get('item_id')}")

# PHASE 7: TOF1
print("\n[7] TOF1 진입 (PP → ToINSP)")
tof1 = J("POST", "/api/debug/sim/conveyor-tof1", json={
    "res_id":"CONV-01","item_id":ITEM_ID,"rfid_payload":payload})
print(f"  → tof1: {tof1}")
print(f"  → item: {DB('SELECT cur_stat, equip_task_type, cur_res FROM public.item WHERE item_id=:p', p=ITEM_ID)}")
print(f"  → pp_task_txn: {DB('SELECT pp_nm, txn_stat FROM public.pp_task_txn WHERE item_id=:p', p=ITEM_ID)}")

# PHASE 8: TOF2
print("\n[8] TOF2 도달 (ToINSP → INSP)")
tof2 = J("POST", "/api/debug/sim/conveyor-tof2", json={"res_id":"CONV-01","item_id":ITEM_ID})
print(f"  → tof2: {tof2}")
insp = DB("SELECT txn_id, txn_stat FROM public.insp_task_txn WHERE item_id=:p", p=ITEM_ID)
print(f"  → insp_task_txn: {insp}")

# PHASE 9: 검사 GP
print("\n[9] 검사 GP")
if insp:
    cinsp = J("POST", f"/api/quality/inspections/{insp[0].txn_id}/result?result=true")
    print(f"  → result: {cinsp}")
print(f"  → item: {DB('SELECT cur_stat, is_defective FROM public.item WHERE item_id=:p', p=ITEM_ID)}")

# PHASE 10: 출하
print("\n[10] DONE → SHIP → COMP")
for stat in ["DONE","SHIP","COMP"]:
    J("POST", f"/api/orders/{ORD_ID}/status?new_stat={stat}")
final = [s.ord_stat for s in DB('SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id', p=ORD_ID)]
print(f"  ✔ ord_stat 추이: {final}")

# 최종 종합
print("\n"+"="*82)
print("[VERIFY] ord_40 풀 라이프사이클 데이터 종합")
print("="*82)
for tbl, q in [
    ("ord",            "SELECT ord_id, user_id, created_at FROM public.ord WHERE ord_id=:p"),
    ("ord_detail",     "SELECT ord_id, qty, due_date, ship_addr FROM public.ord_detail WHERE ord_id=:p"),
    ("ord_stat",       "SELECT ord_stat FROM public.ord_stat WHERE ord_id=:p ORDER BY stat_id"),
    ("ord_pp_map",     "SELECT pp_id FROM public.ord_pp_map WHERE ord_id=:p"),
    ("pattern",        "SELECT ptn_id, ptn_loc FROM public.pattern WHERE ptn_id=:p"),
    ("item",           "SELECT item_id, cur_stat, is_defective FROM public.item WHERE ord_id=:p"),
    ("equip_task_txn", "SELECT txn_id, task_type, txn_stat, res_id FROM public.equip_task_txn WHERE item_id=:i ORDER BY txn_id"),
    ("trans_task_txn", "SELECT trans_task_txn_id, task_type, txn_stat FROM public.trans_task_txn WHERE ord_id=:p"),
    ("pp_task_txn",    "SELECT txn_id, pp_nm, txn_stat FROM public.pp_task_txn WHERE ord_id=:p ORDER BY txn_id"),
    ("insp_task_txn",  "SELECT txn_id, txn_stat, result FROM public.insp_task_txn WHERE item_id=:i"),
    ("rfid_scan_log",  "SELECT id, raw_payload, parse_status FROM public.rfid_scan_log WHERE item_id=:i"),
    ("handoff_acks",   "SELECT id, task_id, zone, ack_source FROM public.handoff_acks WHERE task_id=(SELECT trans_task_txn_id FROM public.trans_task_txn WHERE ord_id=:p LIMIT 1)"),
]:
    rows = DB(q, p=ORD_ID, i=ITEM_ID)
    print(f"  {tbl:18s} {len(rows):2d} rows: {rows[:3]}")

# 웹 API 응답
print("\n[WEB API] PyQt/Next.js 가 보는 동일 endpoint")
print("-"*82)
def G(p):
    r = S.get(BASE+p, timeout=10)
    return r.status_code, r.json() if r.headers.get('content-type','').startswith('application/json') else r.text
sc,d=G(f"/api/orders/{ORD_ID}")
print(f"  GET /api/orders/40 → {sc} latest_stat={d.get('latest_stat')} stats={len(d.get('stats',[]))} pp_options={len(d.get('pp_options',[]))}")
sc,d=G(f"/api/production/items?ord_id={ORD_ID}")
print(f"  GET /api/production/items?ord_id=40 → {sc} {d}")
sc,d=G(f"/api/production/items/{ITEM_ID}/pp")
print(f"  GET /api/production/items/{ITEM_ID}/pp → {sc} pp_options={len(d.get('pp_options',[]))} task_status={len(d.get('pp_task_status',[]))}")
sc,d=G(f"/api/quality/summary/{ORD_ID}")
print(f"  GET /api/quality/summary/40 → {sc} {d}")
