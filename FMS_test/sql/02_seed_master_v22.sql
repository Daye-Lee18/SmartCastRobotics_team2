-- =============================================
-- SmartCast FMS Test Master Seed for DB Schema v22
-- File: FMS_test/seed_master_v22.sql
-- =============================================
-- Purpose:
--   Fill only master/reference tables needed before FMS scenario tests.
--
-- Run order on a fresh DB:
--   1. psql <db_name> -f ../DB/create_tables_v22.sql
--   2. psql <db_name> -f seed_master_v22.sql
--
-- Notes:
--   - This file does NOT insert orders, order details, item states, or task txns.
--   - Product names/codes from the Web UI are kept in comments because v22 product
--     currently has no prod_cd/prod_nm columns.
--   - Product category mapping:
--       round  -> CMH
--       square -> RMH
--       oval   -> EMH
-- =============================================

BEGIN;

-- =====================
-- USER MASTER
-- =====================

INSERT INTO user_account (user_id, co_nm, user_nm, role, phone, email, password) VALUES
(1, 'SmartCast Robotics', '관리자',      'admin',    '010-0000-0000', 'admin@smartcast.kr',    'admin1234'),
(2, 'SmartCast Robotics', '운영자',      'operator', '010-0000-0001', 'operator@smartcast.kr', 'operator1234'),
(3, 'SmartCast Robotics', 'FMS',         'fms',      NULL,            'fms@smartcast.kr',      'fms1234'),
(4, 'TechBuild Inc.',     '이민준',      'customer', '010-3333-4444', 'minjun@techbuild.co',   'customer1234'),
(5, 'BuildWorld Co.',     '정수연',      'customer', '010-9999-0000', 'sooyeon@buildworld.kr', 'customer1234')
ON CONFLICT (user_id) DO UPDATE SET
    co_nm = EXCLUDED.co_nm,
    user_nm = EXCLUDED.user_nm,
    role = EXCLUDED.role,
    phone = EXCLUDED.phone,
    email = EXCLUDED.email,
    password = EXCLUDED.password;

-- =====================
-- PRODUCT MASTER
-- =====================

INSERT INTO category (cate_cd, cate_nm) VALUES
('CMH', '원형 맨홀뚜껑'),
('RMH', '사각 맨홀뚜껑'),
('EMH', '타원형 맨홀뚜껑')
ON CONFLICT (cate_cd) DO UPDATE SET
    cate_nm = EXCLUDED.cate_nm;

-- UI source:
--   1 R-D450 원형 맨홀뚜껑 KS D-450
--   2 R-D500 원형 맨홀뚜껑 KS D-500
--   3 R-D550 원형 맨홀뚜껑 KS D-550
--   4 S-400  사각 맨홀뚜껑 KS S-400
--   5 S-450  사각 맨홀뚜껑 KS S-450
--   6 S-500  사각 맨홀뚜껑 KS S-500
--   7 O-450  타원형 맨홀뚜껑 KS O-450
--   8 O-500  타원형 맨홀뚜껑 KS O-500
--   9 O-550  타원형 맨홀뚜껑 KS O-550
INSERT INTO product (prod_id, cate_cd, base_price, img_url) VALUES
(1, 'CMH', 75000, '/products/round.jpg'),
(2, 'CMH', 82000, '/products/round.jpg'),
(3, 'CMH', 90000, '/products/round.jpg'),
(4, 'RMH', 68000, '/products/square.jpg'),
(5, 'RMH', 78000, '/products/square.jpg'),
(6, 'RMH', 88000, '/products/square.jpg'),
(7, 'EMH', 72000, '/products/oval.jpg'),
(8, 'EMH', 80000, '/products/oval.jpg'),
(9, 'EMH', 88000, '/products/oval.jpg')
ON CONFLICT (prod_id) DO UPDATE SET
    cate_cd = EXCLUDED.cate_cd,
    base_price = EXCLUDED.base_price,
    img_url = EXCLUDED.img_url;

-- Representative orderable product options.
-- diameter stores the main numeric size in mm. For square/oval products,
-- detailed text like 400x400mm is not representable in v22 yet.
INSERT INTO product_option
    (prod_opt_id, prod_id, mat_type, diameter, thickness, material, load_class)
VALUES
-- R-D450
(1,  1, 'CAST', 450, 25, 'FC200',  'B125'),
(2,  1, 'CAST', 450, 30, 'FC250',  'C250'),
(3,  1, 'CAST', 450, 35, 'GCD450', 'D400'),
-- R-D500
(4,  2, 'CAST', 500, 25, 'FC200',  'B125'),
(5,  2, 'CAST', 500, 30, 'FC250',  'C250'),
(6,  2, 'CAST', 500, 35, 'GCD450', 'D400'),
-- R-D550
(7,  3, 'CAST', 550, 30, 'FC200',  'B125'),
(8,  3, 'CAST', 550, 35, 'FC250',  'C250'),
(9,  3, 'CAST', 550, 40, 'GCD450', 'D400'),
-- S-400
(10, 4, 'CAST', 400, 25, 'FC200',  'A15'),
(11, 4, 'CAST', 400, 30, 'FC250',  'B125'),
(12, 4, 'CAST', 400, 35, 'FC250',  'C250'),
-- S-450
(13, 5, 'CAST', 450, 25, 'FC200',  'B125'),
(14, 5, 'CAST', 450, 30, 'FC250',  'C250'),
(15, 5, 'CAST', 450, 35, 'GCD450', 'D400'),
-- S-500
(16, 6, 'CAST', 500, 30, 'FC200',  'B125'),
(17, 6, 'CAST', 500, 35, 'FC250',  'C250'),
(18, 6, 'CAST', 500, 40, 'GCD450', 'D400'),
-- O-450
(19, 7, 'CAST', 450, 25, 'FC200',  'A15'),
(20, 7, 'CAST', 450, 30, 'FC250',  'B125'),
(21, 7, 'CAST', 450, 35, 'FC250',  'C250'),
-- O-500
(22, 8, 'CAST', 500, 25, 'FC200',  'A15'),
(23, 8, 'CAST', 500, 30, 'FC250',  'B125'),
(24, 8, 'CAST', 500, 35, 'FC250',  'C250'),
-- O-550
(25, 9, 'CAST', 550, 30, 'FC200',  'B125'),
(26, 9, 'CAST', 550, 35, 'FC250',  'C250'),
(27, 9, 'CAST', 550, 40, 'GCD450', 'D400')
ON CONFLICT (prod_opt_id) DO UPDATE SET
    prod_id = EXCLUDED.prod_id,
    mat_type = EXCLUDED.mat_type,
    diameter = EXCLUDED.diameter,
    thickness = EXCLUDED.thickness,
    material = EXCLUDED.material,
    load_class = EXCLUDED.load_class;

INSERT INTO pp_options (pp_id, pp_nm, extra_cost) VALUES
(1, '표면 연마',       5000),
(2, '방청 코팅',       3000),
(3, '아연 도금',       8000),
(4, '로고/문구 삽입',  7000)
ON CONFLICT (pp_id) DO UPDATE SET
    pp_nm = EXCLUDED.pp_nm,
    extra_cost = EXCLUDED.extra_cost;

-- =====================
-- FLOW / ZONE / RESOURCE MASTER
-- =====================

INSERT INTO flow_stat_cd (flow_stat) VALUES
('CREATED'),
('CAST'),
('WAIT_PP'),
('PP'),
('WAIT_INSP'),
('INSP'),
('WAIT_PA'),
('PA'),
('STORED'),
('PICK'),
('READY_TO_SHIP'),
('DISCARDED'),
('HOLD')
ON CONFLICT (flow_stat) DO NOTHING;

INSERT INTO zone (zone_id, zone_nm) VALUES
(1, 'CAST'),
(2, 'PP'),
(3, 'INSP'),
(4, 'STRG'),
(5, 'PICK'),
(6, 'SHIP'),
(7, 'CHG')
ON CONFLICT (zone_id) DO UPDATE SET
    zone_nm = EXCLUDED.zone_nm;

INSERT INTO res (res_id, res_type, model_nm) VALUES
('RA1',   'RA',   'JetCobot 280 CAST'),
('RA2',   'RA',   'JetCobot 280 PICK'),
('RA3',   'RA',   'JetCobot 280 SHIP'),
('CONV1', 'CONV', 'ESP32 Conveyor v5 INSP'),
('CONV2', 'CONV', 'ESP32 Conveyor v5 AUX'),
('AMR1',  'AMR',  'TurtleBot3 Burger'),
('AMR2',  'AMR',  'TurtleBot3 Burger')
ON CONFLICT (res_id) DO UPDATE SET
    res_type = EXCLUDED.res_type,
    model_nm = EXCLUDED.model_nm;

INSERT INTO equip (res_id, zone_id) VALUES
('RA1',   1),
('RA2',   5),
('RA3',   6),
('CONV1', 3),
('CONV2', 3)
ON CONFLICT (res_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id;

INSERT INTO equip_load_spec (load_spec_id, load_class, press_f, press_t, tol_val) VALUES
(1, 'A15',  150.00, 1.00, 0.03),
(2, 'B125', 125.00, 1.20, 0.04),
(3, 'C250', 250.00, 1.35, 0.05),
(4, 'D400', 400.00, 1.50, 0.05),
(5, 'E600', 600.00, 2.00, 0.08),
(6, 'F900', 900.00, 2.50, 0.10)
ON CONFLICT (load_spec_id) DO UPDATE SET
    load_class = EXCLUDED.load_class,
    press_f = EXCLUDED.press_f,
    press_t = EXCLUDED.press_t,
    tol_val = EXCLUDED.tol_val;

-- =====================
-- LOCATION / COORD MASTER
-- =====================

-- Insert charge slots first without trans_coord_id because chg_loc_stat and
-- trans_coord reference each other.
INSERT INTO chg_loc_stat (loc_id, zone_id, trans_coord_id, res_id, loc_row, loc_col, status, stored_at) VALUES
(1, 7, NULL, 'AMR1', 1, 1, 'occupied', now()),
(2, 7, NULL, NULL,   1, 2, 'empty',    now()),
(3, 7, NULL, 'AMR2', 1, 3, 'occupied', now())
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    res_id = EXCLUDED.res_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

INSERT INTO trans_coord (trans_coord_id, zone_id, chg_loc_id, x, y, theta) VALUES
(1, 1, NULL,  1.50, 2.30,   0.00),
(2, 2, NULL,  5.20, 2.10,  90.00),
(3, 3, NULL,  9.10, 2.30,   0.00),
(4, 4, NULL, 12.50, 3.00, 180.00),
(5, 5, NULL, 15.30, 2.30,   0.00),
(6, 6, NULL, 18.00, 2.30,   0.00),
(7, 7, 1,     0.50, 8.00, 270.00),
(8, 7, 2,     0.50, 9.00, 270.00),
(9, 7, 3,     1.50, 8.00, 270.00)
ON CONFLICT (trans_coord_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    chg_loc_id = EXCLUDED.chg_loc_id,
    x = EXCLUDED.x,
    y = EXCLUDED.y,
    theta = EXCLUDED.theta;

UPDATE chg_loc_stat SET trans_coord_id = 7 WHERE loc_id = 1;
UPDATE chg_loc_stat SET trans_coord_id = 8 WHERE loc_id = 2;
UPDATE chg_loc_stat SET trans_coord_id = 9 WHERE loc_id = 3;

INSERT INTO strg_loc_stat (loc_id, zone_id, item_stat_id, loc_row, loc_col, status, stored_at)
SELECT
    ((r - 1) * 6 + c) AS loc_id,
    4 AS zone_id,
    NULL::INT AS item_stat_id,
    r AS loc_row,
    c AS loc_col,
    'empty' AS status,
    now() AS stored_at
FROM generate_series(1, 3) AS r,
     generate_series(1, 6) AS c
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    item_stat_id = EXCLUDED.item_stat_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

INSERT INTO ship_loc_stat (loc_id, zone_id, ord_id, item_stat_id, loc_row, loc_col, status, stored_at)
SELECT
    c AS loc_id,
    6 AS zone_id,
    NULL::INT AS ord_id,
    NULL::INT AS item_stat_id,
    1 AS loc_row,
    c AS loc_col,
    'empty' AS status,
    now() AS stored_at
FROM generate_series(1, 5) AS c
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    ord_id = EXCLUDED.ord_id,
    item_stat_id = EXCLUDED.item_stat_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

-- =====================
-- TRANSPORT MASTER
-- =====================

INSERT INTO trans (res_id, slot_count, max_load_kg, home_coord_id) VALUES
('AMR1', 1, 30.0, 7),
('AMR2', 1, 30.0, 9)
ON CONFLICT (res_id) DO UPDATE SET
    slot_count = EXCLUDED.slot_count,
    max_load_kg = EXCLUDED.max_load_kg,
    home_coord_id = EXCLUDED.home_coord_id;

INSERT INTO trans_task_bat_threshold (res_id, task_type, bat_low_threshold) VALUES
('AMR1', 'ToPP',   20),
('AMR1', 'ToSTRG', 25),
('AMR1', 'ToSHIP', 20),
('AMR1', 'ToCHG',  15),
('AMR2', 'ToPP',   20),
('AMR2', 'ToSTRG', 25),
('AMR2', 'ToSHIP', 20),
('AMR2', 'ToCHG',  15)
ON CONFLICT (res_id, task_type) DO UPDATE SET
    bat_low_threshold = EXCLUDED.bat_low_threshold;

-- =====================
-- AI MODEL MASTER
-- =====================

INSERT INTO ai_model (model_id, model_nm, model_type, target_cls, is_active, created_at) VALUES
(1, 'YOLOv8-SmartCast-v1', 'YOLO',      NULL,  TRUE, now()),
(2, 'PatchCore-CMH-v1',    'PATCHCORE', 'CMH', TRUE, now()),
(3, 'PatchCore-RMH-v1',    'PATCHCORE', 'RMH', TRUE, now()),
(4, 'PatchCore-EMH-v1',    'PATCHCORE', 'EMH', TRUE, now())
ON CONFLICT (model_id) DO UPDATE SET
    model_nm = EXCLUDED.model_nm,
    model_type = EXCLUDED.model_type,
    target_cls = EXCLUDED.target_cls,
    is_active = EXCLUDED.is_active;

-- =====================
-- RA MOTION MASTER
-- =====================
-- Minimal reusable motion programs for FMS tests.

INSERT INTO ra_motion_step
    (step_id, task_type, pattern_no, loc_id, pose_nm, step_ord, command_type,
     j1, j2, j3, j4, j5, j6, delta_z, speed, delay_sec)
VALUES
-- MM pattern 1
(1,  'MM', 1, NULL, NULL, 1, 'MOVE_ANGLES',  0.0, -30.0,  60.0, 0.0, 30.0, 0.0, NULL, 50, NULL),
(2,  'MM', 1, NULL, NULL, 2, 'MOVE_Z',       NULL, NULL, NULL, NULL, NULL, NULL, -50.0, 30, NULL),
(3,  'MM', 1, NULL, NULL, 3, 'GRIP_CLOSE',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.5),
(4,  'MM', 1, NULL, NULL, 4, 'MOVE_Z',       NULL, NULL, NULL, NULL, NULL, NULL,  50.0, 30, NULL),
(5,  'MM', 1, NULL, NULL, 5, 'MOVE_ANGLES',  0.0,   0.0,   0.0, 0.0,  0.0, 0.0, NULL, 50, NULL),
-- MM pattern 2
(6,  'MM', 2, NULL, NULL, 1, 'MOVE_ANGLES', 30.0, -30.0,  60.0, 0.0, 30.0, 0.0, NULL, 50, NULL),
(7,  'MM', 2, NULL, NULL, 2, 'MOVE_Z',       NULL, NULL, NULL, NULL, NULL, NULL, -50.0, 30, NULL),
(8,  'MM', 2, NULL, NULL, 3, 'GRIP_CLOSE',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.5),
(9,  'MM', 2, NULL, NULL, 4, 'MOVE_Z',       NULL, NULL, NULL, NULL, NULL, NULL,  50.0, 30, NULL),
(10, 'MM', 2, NULL, NULL, 5, 'MOVE_ANGLES',  0.0,   0.0,   0.0, 0.0,  0.0, 0.0, NULL, 50, NULL),
-- POUR
(11, 'POUR', NULL, NULL, NULL, 1, 'MOVE_ANGLES', 45.0, -45.0, 90.0, 0.0, 45.0, 0.0, NULL, 40, NULL),
(12, 'POUR', NULL, NULL, NULL, 2, 'WAIT',         NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 5.0),
(13, 'POUR', NULL, NULL, NULL, 3, 'MOVE_ANGLES',  0.0,   0.0,  0.0, 0.0,  0.0, 0.0, NULL, 40, NULL),
-- DM
(14, 'DM', NULL, NULL, NULL, 1, 'MOVE_ANGLES', 0.0, -20.0, 45.0, 0.0, 20.0, 0.0, NULL, 50, NULL),
(15, 'DM', NULL, NULL, NULL, 2, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL, -40.0, 30, NULL),
(16, 'DM', NULL, NULL, NULL, 3, 'GRIP_OPEN',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.3),
(17, 'DM', NULL, NULL, NULL, 4, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL,  40.0, 30, NULL),
-- PA_GP to storage loc 1
(18, 'PA_GP', NULL, 1, 'SLOT_PATH', 1, 'MOVE_ANGLES', 10.0, -40.0, 80.0, 0.0, 40.0, 0.0, NULL, 60, NULL),
(19, 'PA_GP', NULL, 1, 'SLOT_PATH', 2, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL, -45.0, 30, NULL),
(20, 'PA_GP', NULL, 1, 'SLOT_PATH', 3, 'GRIP_OPEN',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.3),
(21, 'PA_GP', NULL, 1, 'SLOT_PATH', 4, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL,  45.0, 30, NULL),
-- PA_DP
(22, 'PA_DP', NULL, NULL, 'DEFECT_DROP', 1, 'MOVE_ANGLES', -45.0, -30.0, 60.0, 0.0, 30.0, 0.0, NULL, 40, NULL),
(23, 'PA_DP', NULL, NULL, 'DEFECT_DROP', 2, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL, -30.0, 30, NULL),
(24, 'PA_DP', NULL, NULL, 'DEFECT_DROP', 3, 'GRIP_OPEN',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.3),
(25, 'PA_DP', NULL, NULL, 'DEFECT_DROP', 4, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL,  30.0, 30, NULL),
-- PICK from storage loc 1
(26, 'PICK', NULL, 1, 'AMR_HANDOFF', 1, 'MOVE_ANGLES', 20.0, -50.0, 100.0, 0.0, 50.0, 0.0, NULL, 50, NULL),
(27, 'PICK', NULL, 1, 'AMR_HANDOFF', 2, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL, -40.0, 30, NULL),
(28, 'PICK', NULL, 1, 'AMR_HANDOFF', 3, 'GRIP_CLOSE',  NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.5),
(29, 'PICK', NULL, 1, 'AMR_HANDOFF', 4, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL,  40.0, 30, NULL),
-- SHIP handoff path
(30, 'SHIP', NULL, 1, 'AMR_HANDOFF', 1, 'MOVE_ANGLES', 30.0, -60.0, 120.0, 0.0, 60.0, 0.0, NULL, 50, NULL),
(31, 'SHIP', NULL, 1, 'AMR_HANDOFF', 2, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL, -40.0, 30, NULL),
(32, 'SHIP', NULL, 1, 'AMR_HANDOFF', 3, 'GRIP_OPEN',   NULL, NULL, NULL, NULL, NULL, NULL,  NULL, NULL, 0.3),
(33, 'SHIP', NULL, 1, 'AMR_HANDOFF', 4, 'MOVE_Z',      NULL, NULL, NULL, NULL, NULL, NULL,  40.0, 30, NULL)
ON CONFLICT (step_id) DO UPDATE SET
    task_type = EXCLUDED.task_type,
    pattern_no = EXCLUDED.pattern_no,
    loc_id = EXCLUDED.loc_id,
    pose_nm = EXCLUDED.pose_nm,
    step_ord = EXCLUDED.step_ord,
    command_type = EXCLUDED.command_type,
    j1 = EXCLUDED.j1,
    j2 = EXCLUDED.j2,
    j3 = EXCLUDED.j3,
    j4 = EXCLUDED.j4,
    j5 = EXCLUDED.j5,
    j6 = EXCLUDED.j6,
    delta_z = EXCLUDED.delta_z,
    speed = EXCLUDED.speed,
    delay_sec = EXCLUDED.delay_sec;

-- =====================
-- RESET SEQUENCES
-- =====================

SELECT setval('user_account_user_id_seq',   (SELECT MAX(user_id) FROM user_account));
SELECT setval('product_prod_id_seq',        (SELECT MAX(prod_id) FROM product));
SELECT setval('product_option_prod_opt_id_seq', (SELECT MAX(prod_opt_id) FROM product_option));
SELECT setval('pp_options_pp_id_seq',       (SELECT MAX(pp_id) FROM pp_options));
SELECT setval('zone_zone_id_seq',           (SELECT MAX(zone_id) FROM zone));
SELECT setval('equip_load_spec_load_spec_id_seq', (SELECT MAX(load_spec_id) FROM equip_load_spec));
SELECT setval('chg_loc_stat_loc_id_seq',    (SELECT MAX(loc_id) FROM chg_loc_stat));
SELECT setval('trans_coord_trans_coord_id_seq', (SELECT MAX(trans_coord_id) FROM trans_coord));
SELECT setval('strg_loc_stat_loc_id_seq',   (SELECT MAX(loc_id) FROM strg_loc_stat));
SELECT setval('ship_loc_stat_loc_id_seq',   (SELECT MAX(loc_id) FROM ship_loc_stat));
SELECT setval('ai_model_model_id_seq',      (SELECT MAX(model_id) FROM ai_model));
SELECT setval('ra_motion_step_step_id_seq', (SELECT MAX(step_id) FROM ra_motion_step));

COMMIT;

-- Verification summary.
SELECT 'user_account' AS table_name, COUNT(*) AS row_count FROM user_account
UNION ALL SELECT 'category', COUNT(*) FROM category
UNION ALL SELECT 'product', COUNT(*) FROM product
UNION ALL SELECT 'product_option', COUNT(*) FROM product_option
UNION ALL SELECT 'pp_options', COUNT(*) FROM pp_options
UNION ALL SELECT 'zone', COUNT(*) FROM zone
UNION ALL SELECT 'res', COUNT(*) FROM res
UNION ALL SELECT 'equip', COUNT(*) FROM equip
UNION ALL SELECT 'equip_load_spec', COUNT(*) FROM equip_load_spec
UNION ALL SELECT 'chg_loc_stat', COUNT(*) FROM chg_loc_stat
UNION ALL SELECT 'trans_coord', COUNT(*) FROM trans_coord
UNION ALL SELECT 'strg_loc_stat', COUNT(*) FROM strg_loc_stat
UNION ALL SELECT 'ship_loc_stat', COUNT(*) FROM ship_loc_stat
UNION ALL SELECT 'trans', COUNT(*) FROM trans
UNION ALL SELECT 'trans_task_bat_threshold', COUNT(*) FROM trans_task_bat_threshold
UNION ALL SELECT 'ai_model', COUNT(*) FROM ai_model
UNION ALL SELECT 'ra_motion_step', COUNT(*) FROM ra_motion_step
ORDER BY table_name;
