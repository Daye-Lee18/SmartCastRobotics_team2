-- =============================================
-- 마스터 데이터 seed — smartcast schema
-- Idempotent: ON CONFLICT DO NOTHING
-- =============================================

SET search_path TO smartcast, public;

-- ---------- category (Confluence 32342045 약어 사전 기준) ----------
INSERT INTO smartcast.category (cate_cd, cate_nm) VALUES
    ('CMH', '원형맨홀'),
    ('RMH', '사각맨홀'),
    ('EMH', '타원맨홀')
ON CONFLICT (cate_cd) DO NOTHING;

-- ---------- pp_options (후처리 4종) ----------
INSERT INTO smartcast.pp_options (pp_nm, extra_cost) VALUES
    ('표면연마',     50000),
    ('방청코팅',     80000),
    ('아연도금',    120000),
    ('로고문구삽입', 60000)
ON CONFLICT (pp_nm) DO NOTHING;

-- ---------- zone (공정 6구역) ----------
INSERT INTO smartcast.zone (zone_nm) VALUES
    ('CAST'),
    ('PP'),
    ('INSP'),
    ('STRG'),
    ('SHIP'),
    ('CHG')
ON CONFLICT (zone_nm) DO NOTHING;

-- ---------- res (자원 마스터: RA1-3, CONV1, AMR1-2) ----------
INSERT INTO smartcast.res (res_id, res_type, model_nm) VALUES
    ('RA1',   'RA',   'JetCobot 280'),
    ('RA2',   'RA',   'JetCobot 280'),
    ('RA3',   'RA',   'JetCobot 280'),
    ('CONV1', 'CONV', 'ESP32 Conveyor v5'),
    ('AMR1',  'AMR',  'TurtleBot3 Burger'),
    ('AMR2',  'AMR',  'TurtleBot3 Burger')
ON CONFLICT (res_id) DO NOTHING;

-- ---------- equip (생산 설비: RA1-3, CONV1) ----------
INSERT INTO smartcast.equip (res_id, zone_id) VALUES
    ('RA1',   (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'CAST')),
    ('RA2',   (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'STRG')),
    ('RA3',   (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'SHIP')),
    ('CONV1', (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'INSP'))
ON CONFLICT (res_id) DO NOTHING;

-- ---------- trans (이송 자원: AMR1-2) ----------
INSERT INTO smartcast.trans (res_id, slot_count, max_load_kg) VALUES
    ('AMR1', 1, 30.0),
    ('AMR2', 1, 30.0)
ON CONFLICT (res_id) DO NOTHING;

-- ---------- chg_location_stat (1x3 충전 위치) ----------
INSERT INTO smartcast.chg_location_stat (zone_id, res_id, loc_row, loc_col, status)
SELECT (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'CHG'),
       NULL, 1, c, 'empty'
FROM generate_series(1, 3) AS c
ON CONFLICT DO NOTHING;

-- ---------- strg_location_stat (3x6 적재 위치, 18칸) ----------
INSERT INTO smartcast.strg_location_stat (zone_id, item_id, loc_row, loc_col, status)
SELECT (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'STRG'),
       NULL, r, c, 'empty'
FROM generate_series(1, 3) AS r,
     generate_series(1, 6) AS c
ON CONFLICT DO NOTHING;

-- ---------- ship_location_stat (1x5 출고 위치, 5칸) ----------
INSERT INTO smartcast.ship_location_stat (zone_id, ord_id, item_id, loc_row, loc_col, status)
SELECT (SELECT zone_id FROM smartcast.zone WHERE zone_nm = 'SHIP'),
       NULL, NULL, 1, c, 'empty'
FROM generate_series(1, 5) AS c
ON CONFLICT DO NOTHING;

-- ---------- 기본 admin 계정 (개발용; password는 평문 — 프로덕션 전 hash 적용 필요) ----------
INSERT INTO smartcast.user_account (co_nm, user_nm, role, phone, email, password) VALUES
    ('SmartCast Robotics', '관리자',  'admin',    '010-0000-0000', 'admin@smartcast.kr',    'admin1234'),
    ('SmartCast Robotics', '운영자',  'operator', '010-0000-0001', 'operator@smartcast.kr', 'operator1234'),
    ('SmartCast Robotics', 'FMS',     'fms',      NULL,            'fms@smartcast.kr',      'fms1234')
ON CONFLICT (email) DO NOTHING;

-- ---------- 검증 ----------
SELECT 'category'   AS tbl, COUNT(*) FROM smartcast.category
UNION ALL SELECT 'pp_options',          COUNT(*) FROM smartcast.pp_options
UNION ALL SELECT 'zone',                COUNT(*) FROM smartcast.zone
UNION ALL SELECT 'res',                 COUNT(*) FROM smartcast.res
UNION ALL SELECT 'equip',               COUNT(*) FROM smartcast.equip
UNION ALL SELECT 'trans',               COUNT(*) FROM smartcast.trans
UNION ALL SELECT 'chg_location_stat',   COUNT(*) FROM smartcast.chg_location_stat
UNION ALL SELECT 'strg_location_stat',  COUNT(*) FROM smartcast.strg_location_stat
UNION ALL SELECT 'ship_location_stat',  COUNT(*) FROM smartcast.ship_location_stat
UNION ALL SELECT 'user_account',        COUNT(*) FROM smartcast.user_account
ORDER BY tbl;
