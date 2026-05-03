-- ============================================================
-- SmartCast FMS Master Seed Data
-- Source of truth for schema: server/smart_cast_db/schema/create_tables.sql
-- ============================================================
-- Purpose:
--   Fill master/reference tables needed before FMS scenario tests.
--
-- Run order on a fresh DB:
--   1. python scripts/01_create_tables.py
--   2. python scripts/02_seed_master.py
-- ============================================================

BEGIN;

-- =====================
-- USER MASTER
-- =====================

INSERT INTO user_account (co_nm, user_nm, role, phone, email, password) VALUES
('SmartCast Robotics', '관리자',      'admin',    '010-0000-0000', 'admin@smartcast.kr',    'admin1234'),
('SmartCast Robotics', '운영자',      'operator', '010-0000-0001', 'operator@smartcast.kr', 'operator1234'),
('SmartCast Robotics', 'FMS',         'fms',      NULL,            'fms@smartcast.kr',      'fms1234'),
('TechBuild Inc.',     '이민준',      'customer', '010-3333-4444', 'minjun@techbuild.co',   'customer1234'),
('BuildWorld Co.',     '정수연',      'customer', '010-9999-0000', 'sooyeon@buildworld.kr', 'customer1234')
ON CONFLICT (email) DO UPDATE SET
    co_nm = EXCLUDED.co_nm,
    user_nm = EXCLUDED.user_nm,
    role = EXCLUDED.role,
    phone = EXCLUDED.phone,
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

-- UI product codes:
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

INSERT INTO product_order_pattern_master
    (prod_id, diameter, thickness, material, load_class, pp_mask, pattern_nm, is_active)
SELECT
    po.prod_id,
    po.diameter,
    po.thickness,
    po.material,
    po.load_class,
    pp_mask.mask AS pp_mask,
    format('PAT-P%s-PP%s', po.prod_opt_id, pp_mask.mask) AS pattern_nm,
    TRUE AS is_active
FROM product_option po
CROSS JOIN generate_series(0, 15) AS pp_mask(mask)
ON CONFLICT (prod_id, diameter, thickness, material, load_class, pp_mask) DO UPDATE SET
    pattern_nm = EXCLUDED.pattern_nm,
    is_active = EXCLUDED.is_active;

INSERT INTO pattern_master (ptn_id, ptn_nm, task_type, description, is_active) VALUES
(1, 'MM pattern 1', 'MM', 'pattern_1(mc) 기준 모션 시퀀스', TRUE),
(2, 'MM pattern 2', 'MM', 'pattern_2(mc) 기준 모션 시퀀스', TRUE),
(3, 'MM pattern 3', 'MM', 'pattern_3(mc) 기준 모션 시퀀스', TRUE)
ON CONFLICT (ptn_id) DO UPDATE SET
    ptn_nm = EXCLUDED.ptn_nm,
    task_type = EXCLUDED.task_type,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active;

-- =====================
-- ZONE / RESOURCE MASTER
-- =====================

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

-- PAT: RA for Putaway (in STRG zone) (putaway arm tool)
-- MAT: RA for manufacturing (manufacturing arm tool)
-- TAT: TAT for transport (transport TAT tool)
INSERT INTO res (res_id, res_type, model_nm) VALUES
('PAT',   'RA',   'JetCobot 280 CAST'),
('MAT',   'RA',   'JetCobot 280 STRG'),
('CONV1', 'CONV', 'ESP32 Conveyor v5 INSP'),
('TAT1',  'TAT',  'PinkyPro'),
('TAT2',  'TAT',  'PinkyPro'),
('TAT3',  'TAT',  'PinkyPro')
ON CONFLICT (res_id) DO UPDATE SET
    res_type = EXCLUDED.res_type,
    model_nm = EXCLUDED.model_nm;

INSERT INTO equip (res_id, zone_id) VALUES
('PAT',   1),
('MAT',   4),
('CONV1', 3)
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
-- LOCATION MASTER
-- =====================

INSERT INTO chg_location_stat (loc_id, zone_id, res_id, loc_row, loc_col, status, stored_at) VALUES
(1, 7, 'TAT1', 1, 1, 'occupied', now()),
(2, 7, 'TAT2', 1, 2, 'occupied', now()),
(3, 7, 'TAT3', 1, 3, 'occupied', now())
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    res_id = EXCLUDED.res_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

INSERT INTO strg_location_stat (loc_id, zone_id, item_id, loc_row, loc_col, status, stored_at)
SELECT
    ((r - 1) * 6 + c) AS loc_id,
    4 AS zone_id,
    NULL::INT AS item_id,
    r AS loc_row,
    c AS loc_col,
    'empty' AS status,
    now() AS stored_at
FROM generate_series(1, 3) AS r,
     generate_series(1, 6) AS c
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    item_id = EXCLUDED.item_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

INSERT INTO ship_location_stat (loc_id, zone_id, ord_id, item_id, loc_row, loc_col, status, stored_at)
SELECT
    c AS loc_id,
    6 AS zone_id,
    NULL::INT AS ord_id,
    NULL::INT AS item_id,
    1 AS loc_row,
    c AS loc_col,
    'empty' AS status,
    now() AS stored_at
FROM generate_series(1, 5) AS c
ON CONFLICT (loc_id) DO UPDATE SET
    zone_id = EXCLUDED.zone_id,
    ord_id = EXCLUDED.ord_id,
    item_id = EXCLUDED.item_id,
    loc_row = EXCLUDED.loc_row,
    loc_col = EXCLUDED.loc_col,
    status = EXCLUDED.status;

-- =====================
-- TRANSPORT MASTER
-- =====================

INSERT INTO trans (res_id, slot_count, max_load_kg) VALUES
('TAT1', 1, 30.0),
('TAT2', 1, 30.0),
('TAT3', 1, 30.0)
ON CONFLICT (res_id) DO UPDATE SET
    slot_count = EXCLUDED.slot_count,
    max_load_kg = EXCLUDED.max_load_kg;

INSERT INTO trans_task_bat_threshold (res_id, task_type, bat_low_threshold) VALUES
('TAT1', 'ToPP',   20),
('TAT1', 'ToSTRG', 25),
('TAT1', 'ToSHIP', 20),
('TAT1', 'ToCHG',  15),
('TAT2', 'ToPP',   20),
('TAT2', 'ToSTRG', 25),
('TAT2', 'ToSHIP', 20),
('TAT2', 'ToCHG',  15),
('TAT3', 'ToPP',   20),
('TAT3', 'ToSTRG', 25),
('TAT3', 'ToSHIP', 20),
('TAT3', 'ToCHG',  15)
ON CONFLICT (res_id, task_type) DO UPDATE SET
    bat_low_threshold = EXCLUDED.bat_low_threshold;

INSERT INTO tat_nav_pose_master
    (pose_id, pose_nm, zone_id, loc_id, pose_x, pose_y, pose_theta, is_active)
VALUES
(1, 'ToINSP', 3, NULL, -0.67,  -0.10, -1.57, TRUE),
(2, 'ToSHIP', 6, NULL, -0.67,   0.45,  1.57, TRUE),
(3, 'ToCAST', 1, NULL, -0.256,  0.20,  1.57, TRUE),
(4, 'ToCHG1', 7, 1,     0.044,  0.095,  0.00, TRUE),
(5, 'ToCHG2', 7, 2,     0.044, -0.027,  0.00, TRUE),
(6, 'ToCHG3', 7, 3,     0.044, -0.179,  0.00, TRUE),
(7, 'ToSTRG', 4, NULL, -0.10,  -0.465, -1.57, TRUE),
(8, 'ToPICK', 5, NULL, -0.223, -0.465, -1.57, TRUE),
(9, 'ToPP',   2, NULL, -0.447, -1.05,   3.14, TRUE)
ON CONFLICT (pose_id) DO UPDATE SET
    pose_nm = EXCLUDED.pose_nm,
    zone_id = EXCLUDED.zone_id,
    loc_id = EXCLUDED.loc_id,
    pose_x = EXCLUDED.pose_x,
    pose_y = EXCLUDED.pose_y,
    pose_theta = EXCLUDED.pose_theta,
    is_active = EXCLUDED.is_active;

-- =====================
-- AI MODEL MASTER
-- =====================

INSERT INTO ai_model (model_id, model_nm, model_type, target_cls, is_active, created_at) VALUES
(1, 'YOLOv26_nano', 'YOLO',      NULL,  TRUE, now()),
(2, 'PatchCore-CMH-v1',    'PATCHCORE', 'CMH', TRUE, now()),
(3, 'PatchCore-RMH-v1',    'PATCHCORE', 'RMH', TRUE, now()),
(4, 'PatchCore-EMH-v1',    'PATCHCORE', 'EMH', TRUE, now())
ON CONFLICT (model_id) DO UPDATE SET
    model_nm = EXCLUDED.model_nm,
    model_type = EXCLUDED.model_type,
    target_cls = EXCLUDED.target_cls,
    is_active = EXCLUDED.is_active;

INSERT INTO ra_motion_step
    (step_id, task_type, pattern_no, loc_id, pose_nm, step_ord, command_type,
     j1, j2, j3, j4, j5, j6, speed, delay_sec, delta_z)
VALUES
-- MM pattern 1
(1, 'MM', 1, NULL, NULL, 1, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(2, 'MM', 1, NULL, NULL, 2, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(3, 'MM', 1, NULL, NULL, 3, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(4, 'MM', 1, NULL, NULL, 4, 'MOVE_ANGLES', 90, 17.5, -144.8, 38, 0, 45, 50, 3, NULL),
(5, 'MM', 1, NULL, NULL, 5, 'GRIP_CLOSE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(6, 'MM', 1, NULL, NULL, 6, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, 50),
(7, 'MM', 1, NULL, NULL, 7, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(8, 'MM', 1, NULL, NULL, 8, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(9, 'MM', 1, NULL, NULL, 9, 'MOVE_ANGLES', 0, 0, 0, -17.31, 0, -45, 50, 1, NULL),
(10, 'MM', 1, NULL, NULL, 10, 'MOVE_ANGLES', 0, -76.6, 0, -17.31, 0, -45, 100, 1, NULL),
(11, 'MM', 1, NULL, NULL, 11, 'MOVE_ANGLES', 0, 0, 0, 0, 0, -45, 50, 1, NULL),
(12, 'MM', 1, NULL, NULL, 12, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(13, 'MM', 1, NULL, NULL, 13, 'MOVE_ANGLES', 90, 25.2, -111.5, -7, 0, 45, 50, 1, NULL),
(14, 'MM', 1, NULL, NULL, 14, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, -60),
(15, 'MM', 1, NULL, NULL, 15, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(16, 'MM', 1, NULL, NULL, 16, 'MOVE_ANGLES', 90, 25.2, -111.5, -7, 0, 45, 50, 1, NULL),
(17, 'MM', 1, NULL, NULL, 17, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
-- MM pattern 2
-- pattern_2(mc)
(18, 'MM', 2, NULL, NULL, 1, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(19, 'MM', 2, NULL, NULL, 2, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(20, 'MM', 2, NULL, NULL, 3, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(21, 'MM', 2, NULL, NULL, 4, 'MOVE_ANGLES', 90, -16, -114, 42, 0, 45, 50, 1, NULL),
(22, 'MM', 2, NULL, NULL, 5, 'GRIP_CLOSE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(23, 'MM', 2, NULL, NULL, 6, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, 50),
(24, 'MM', 2, NULL, NULL, 7, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(25, 'MM', 2, NULL, NULL, 8, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(26, 'MM', 2, NULL, NULL, 9, 'MOVE_ANGLES', 0, 0, 0, -17.31, 0, -45, 50, 1, NULL),
(27, 'MM', 2, NULL, NULL, 10, 'MOVE_ANGLES', 0, -76.6, 0, -17.31, 0, -45, 100, 1, NULL),
(28, 'MM', 2, NULL, NULL, 11, 'MOVE_ANGLES', 0, 0, 0, 0, 0, -45, 50, 1, NULL),
(29, 'MM', 2, NULL, NULL, 12, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(30, 'MM', 2, NULL, NULL, 13, 'MOVE_ANGLES', 90, -10, -63, -17, 0, 45, 50, 1, NULL),
(31, 'MM', 2, NULL, NULL, 14, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, -70),
(32, 'MM', 2, NULL, NULL, 15, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(33, 'MM', 2, NULL, NULL, 16, 'MOVE_ANGLES', 90, -11.2, -63.3, -22.5, 0, 45, 50, 1, NULL),
(34, 'MM', 2, NULL, NULL, 17, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
-- MM pattern 3
-- pattern_3(mc)
(35, 'MM', 3, NULL, NULL, 1, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(36, 'MM', 3, NULL, NULL, 2, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(37, 'MM', 3, NULL, NULL, 3, 'MOVE_ANGLES', 90, 0, 0, -90, 0, 45, 50, 1, NULL),
(38, 'MM', 3, NULL, NULL, 4, 'MOVE_ANGLES', 90, -43, -69, 23, 0, 45, 50, 1, NULL),
(39, 'MM', 3, NULL, NULL, 5, 'GRIP_CLOSE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(40, 'MM', 3, NULL, NULL, 6, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, 50),
(41, 'MM', 3, NULL, NULL, 7, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(42, 'MM', 3, NULL, NULL, 8, 'MOVE_ANGLES', 0, 0, 0, -17.31, 0, -45, 50, 1, NULL),
(43, 'MM', 3, NULL, NULL, 9, 'MOVE_ANGLES', 0, -76.6, 0, -17.31, 0, -45, 100, 1, NULL),
(44, 'MM', 3, NULL, NULL, 10, 'MOVE_ANGLES', 0, 0, 0, 0, 0, -45, 50, 1, NULL),
(45, 'MM', 3, NULL, NULL, 11, 'MOVE_ANGLES', 90, 0, 0, 0, 0, 45, 50, 1, NULL),
(46, 'MM', 3, NULL, NULL, 12, 'MOVE_ANGLES', 90, 0, 0, -90, 0, 45, 50, 1, NULL),
(47, 'MM', 3, NULL, NULL, 13, 'MOVE_ANGLES', 90, -36.12, -63.28, 9.05, 0, 45, 50, 1, NULL),
(48, 'MM', 3, NULL, NULL, 14, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, -10),
(49, 'MM', 3, NULL, NULL, 15, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(50, 'MM', 3, NULL, NULL, 16, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, 60),
(51, 'MM', 3, NULL, NULL, 17, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
-- POUR
(52, 'POUR', NULL, NULL, NULL, 1, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(53, 'POUR', NULL, NULL, NULL, 2, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(54, 'POUR', NULL, NULL, NULL, 3, 'MOVE_ANGLES', -90, 0, 0, 0, 0, 45, 50, 1, NULL),
(55, 'POUR', NULL, NULL, NULL, 4, 'MOVE_ANGLES', -90, -86, 0, 90, 0, 45, 50, 1, NULL),
(56, 'POUR', NULL, NULL, NULL, 5, 'GRIP_CLOSE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(57, 'POUR', NULL, NULL, NULL, 6, 'MOVE_ANGLES', -90, 0, 0, 0, 0, 45, 50, 1, NULL),
(58, 'POUR', NULL, NULL, NULL, 7, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(59, 'POUR', NULL, NULL, NULL, 8, 'MOVE_ANGLES', 0, 0, -142, 143, 1, 45, 50, 1, NULL),
(60, 'POUR', NULL, NULL, NULL, 9, 'MOVE_ANGLES', 0, 0, -142, 143, 1, 125, 10, 10, NULL),
(61, 'POUR', NULL, NULL, NULL, 10, 'MOVE_ANGLES', 0, 0, -142, 143, 1, 45, 50, 1, NULL),
(62, 'POUR', NULL, NULL, NULL, 11, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(63, 'POUR', NULL, NULL, NULL, 12, 'MOVE_ANGLES', -90, 0, 0, 0, 0, 45, 50, 1, NULL),
(64, 'POUR', NULL, NULL, NULL, 13, 'MOVE_ANGLES', -90, -87, 0, 90, 0, 45, 50, 1, NULL),
(65, 'POUR', NULL, NULL, NULL, 14, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(66, 'POUR', NULL, NULL, NULL, 15, 'MOVE_ANGLES', -90, 0, 0, 0, 0, 45, 50, 1, NULL),
(67, 'POUR', NULL, NULL, NULL, 16, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
-- DEMOLDING
(68, 'DM', NULL, NULL, NULL, 1, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(69, 'DM', NULL, NULL, NULL, 2, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(70, 'DM', NULL, NULL, NULL, 3, 'MOVE_ANGLES', 0, 0, 0, -17.31, 0, 45, 50, 1, NULL),
(71, 'DM', NULL, NULL, NULL, 4, 'MOVE_ANGLES', 0, -76.6, 0, -17.31, 0, 45, 100, 1, NULL),
(72, 'DM', NULL, NULL, NULL, 5, 'MOVE_Z', NULL, NULL, NULL, NULL, NULL, NULL, 30, 2, -10),
(73, 'DM', NULL, NULL, NULL, 6, 'GRIP_CLOSE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0.5, NULL),
(74, 'DM', NULL, NULL, NULL, 7, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
(75, 'DM', NULL, NULL, NULL, 8, 'MOVE_ANGLES', -30.9, -60.3, 0, 24, 0, 45, 50, 1, NULL),
(76, 'DM', NULL, NULL, NULL, 9, 'GRIP_OPEN', NULL, NULL, NULL, NULL, NULL, NULL, 100, 1, NULL),
(77, 'DM', NULL, NULL, NULL, 10, 'MOVE_ANGLES', 0, 0, 0, 0, 0, 45, 50, 1, NULL),
-- PA_GP to storage loc 1
(78, 'PA_GP', NULL, NULL, 'HOME',         1, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(79, 'PA_GP', NULL, NULL, 'HOME',         2, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(80, 'PA_GP', NULL, NULL, 'TAT_HANDOFF',  3, 'MOVE_ANGLES',  90, -20.39, -36.56, -7.99, 0, 45, 30, 1, NULL),
(81, 'PA_GP', NULL, NULL, 'TAT_HANDOFF',  4, 'GRIP_CLOSE',   NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(82, 'PA_GP', NULL, NULL, 'HOME',         5, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(83, 'PA_GP', NULL, 1, 'SLOT_PATH',        6, 'MOVE_ANGLES',   4, 0, 0, 0, 0, 45,  50, 2, NULL),
(84, 'PA_GP', NULL, 1, 'SLOT_PATH',        7, 'MOVE_ANGLES',   4, 61.5, -150, 93.2, 0, 45, 30, 2, NULL),
(85, 'PA_GP', NULL, 1, 'SLOT_PATH',        8, 'MOVE_ANGLES',   6, 61.5, -150, 70, 0, 45, 30, 2, NULL),
(86, 'PA_GP', NULL, 1, 'SLOT_PATH',        9, 'MOVE_ANGLES',   6, 8.3, -127.3, 93, 0, 45, 30, 2, NULL),
(87, 'PA_GP', NULL, 1, 'SLOT_PATH',       10, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(88, 'PA_GP', NULL, 1, 'SLOT_PATH',       11, 'MOVE_ANGLES',   6, 8.3, -127.3, 93, 0, 45, 30, 2, NULL),
(89, 'PA_GP', NULL, 1, 'SLOT_PATH',       12, 'MOVE_ANGLES',   6, 61.5, -150, 70, 0, 45, 50, 2, NULL),
(90, 'PA_GP', NULL, 1, 'SLOT_PATH',       13, 'MOVE_ANGLES',   4, 61.5, -150, 93.2, 0, 45, 50, 2, NULL),
(91, 'PA_GP', NULL, 1, 'SLOT_PATH',       14, 'MOVE_ANGLES',   4, 0, 0, 0, 0, 45, 50, 2, NULL),
(92, 'PA_GP', NULL, NULL, 'HOME',         15, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
-- PICK from storage loc 1
(93, 'PICK', NULL, NULL, 'HOME',          1, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(94, 'PICK', NULL, NULL, 'HOME',          2, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(95, 'PICK', NULL, 1, 'SLOT_PATH',         3, 'MOVE_ANGLES',   4, 0, 0, 0, 0, 45,  50, 2, NULL),
(96, 'PICK', NULL, 1, 'SLOT_PATH',         4, 'MOVE_ANGLES',   4, 61.5, -150, 93.2, 0, 45, 30, 2, NULL),
(97, 'PICK', NULL, 1, 'SLOT_PATH',         5, 'MOVE_ANGLES',   6, 61.5, -150, 70, 0, 45, 30, 2, NULL),
(98, 'PICK', NULL, 1, 'SLOT_PATH',         6, 'MOVE_ANGLES',   6, 8.3, -127.3, 93, 0, 45, 30, 2, NULL),
(99, 'PICK', NULL, 1, 'SLOT_PATH',         7, 'GRIP_CLOSE',   NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(100, 'PICK', NULL, 1, 'SLOT_PATH',        8, 'MOVE_ANGLES',   6, 8.3, -127.3, 93, 0, 45, 30, 2, NULL),
(101, 'PICK', NULL, 1, 'SLOT_PATH',        9, 'MOVE_ANGLES',   6, 61.5, -150, 70, 0, 45, 50, 2, NULL),
(102, 'PICK', NULL, 1, 'SLOT_PATH',       10, 'MOVE_ANGLES',   4, 61.5, -150, 93.2, 0, 45, 50, 2, NULL),
(103, 'PICK', NULL, 1, 'SLOT_PATH',       11, 'MOVE_ANGLES',   4, 0, 0, 0, 0, 45, 50, 2, NULL),
(104, 'PICK', NULL, NULL, 'TAT_HANDOFF',  12, 'MOVE_ANGLES',  90, -20.39, -36.56, -7.99, 0, 45, 30, 2, NULL),
(105, 'PICK', NULL, NULL, 'TAT_HANDOFF',  13, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(106, 'PICK', NULL, NULL, 'HOME',         14, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
-- PA_DP
(107, 'PA_DP', NULL, NULL, 'HOME',         1, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(108, 'PA_DP', NULL, NULL, 'HOME',         2, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(109, 'PA_DP', NULL, NULL, 'TAT_HANDOFF',  3, 'MOVE_ANGLES',  90, -20.39, -36.56, -7.99, 0, 45, 30, 1, NULL),
(110, 'PA_DP', NULL, NULL, 'TAT_HANDOFF',  4, 'GRIP_CLOSE',   NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(111, 'PA_DP', NULL, NULL, 'HOME',         5, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(112, 'PA_DP', NULL, NULL, 'DEFECT_HOVER', 6, 'MOVE_ANGLES', -110, 0, 0, 0, 0, 45, 50, 3, NULL),
(113, 'PA_DP', NULL, NULL, 'DEFECT_DROP',  7, 'MOVE_ANGLES', -110, -70, 0, 0, 0, 45, 30, 1, NULL),
(114, 'PA_DP', NULL, NULL, 'DEFECT_DROP',  8, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(115, 'PA_DP', NULL, NULL, 'DEFECT_HOVER', 9, 'MOVE_ANGLES', -110, 0, 0, 0, 0, 45, 50, 3, NULL),
(116, 'PA_DP', NULL, NULL, 'HOME',        10, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
-- SHIP handoff path
(117, 'SHIP', NULL, NULL, 'HOME',          1, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL),
(118, 'SHIP', NULL, NULL, 'HOME',          2, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(119, 'SHIP', NULL, NULL, 'TAT_HANDOFF',   3, 'MOVE_ANGLES',  90, -20.39, -36.56, -7.99, 0, 45, 30, 2, NULL),
(120, 'SHIP', NULL, NULL, 'TAT_HANDOFF',   4, 'GRIP_OPEN',    NULL, NULL, NULL, NULL, NULL, NULL, 50, 1, NULL),
(121, 'SHIP', NULL, NULL, 'HOME',          5, 'MOVE_ANGLES',  90, 0, 0, 0, 0, 45,  50, 1, NULL)
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

UPDATE ra_motion_step
SET tool_type = CASE
    WHEN task_type IN ('PA_GP', 'PA_DP', 'PICK', 'SHIP') THEN 'PAT'
    ELSE 'MAT'
END;

-- =====================
-- RESET SEQUENCES
-- =====================

SELECT setval('user_account_user_id_seq',        (SELECT MAX(user_id)      FROM user_account));
SELECT setval('product_prod_id_seq',             (SELECT MAX(prod_id)      FROM product));
SELECT setval('product_option_prod_opt_id_seq',  (SELECT MAX(prod_opt_id)  FROM product_option));
SELECT setval('pp_options_pp_id_seq',            (SELECT MAX(pp_id)        FROM pp_options));
SELECT setval('product_order_pattern_master_pattern_id_seq', (SELECT MAX(pattern_id) FROM product_order_pattern_master));
SELECT setval('zone_zone_id_seq',                (SELECT MAX(zone_id)      FROM zone));
SELECT setval('equip_load_spec_load_spec_id_seq',(SELECT MAX(load_spec_id) FROM equip_load_spec));
SELECT setval('chg_location_stat_loc_id_seq',    (SELECT MAX(loc_id)       FROM chg_location_stat));
SELECT setval('strg_location_stat_loc_id_seq',   (SELECT MAX(loc_id)       FROM strg_location_stat));
SELECT setval('ship_location_stat_loc_id_seq',   (SELECT MAX(loc_id)       FROM ship_location_stat));
SELECT setval('tat_nav_pose_master_pose_id_seq', (SELECT MAX(pose_id)      FROM tat_nav_pose_master));
SELECT setval('ai_model_model_id_seq',           (SELECT MAX(model_id)     FROM ai_model));
SELECT setval('ra_motion_step_step_id_seq',      (SELECT MAX(step_id)      FROM ra_motion_step));

COMMIT;

-- Verification summary
SELECT 'user_account'             AS table_name, COUNT(*) AS row_count FROM user_account
UNION ALL SELECT 'category',             COUNT(*) FROM category
UNION ALL SELECT 'product',              COUNT(*) FROM product
UNION ALL SELECT 'product_option',       COUNT(*) FROM product_option
UNION ALL SELECT 'pp_options',           COUNT(*) FROM pp_options
UNION ALL SELECT 'product_order_pattern_master', COUNT(*) FROM product_order_pattern_master
UNION ALL SELECT 'pattern_master',       COUNT(*) FROM pattern_master
UNION ALL SELECT 'zone',                 COUNT(*) FROM zone
UNION ALL SELECT 'res',                  COUNT(*) FROM res
UNION ALL SELECT 'equip',               COUNT(*) FROM equip
UNION ALL SELECT 'equip_load_spec',      COUNT(*) FROM equip_load_spec
UNION ALL SELECT 'chg_location_stat',    COUNT(*) FROM chg_location_stat
UNION ALL SELECT 'strg_location_stat',   COUNT(*) FROM strg_location_stat
UNION ALL SELECT 'ship_location_stat',   COUNT(*) FROM ship_location_stat
UNION ALL SELECT 'trans',                COUNT(*) FROM trans
UNION ALL SELECT 'trans_task_bat_threshold', COUNT(*) FROM trans_task_bat_threshold
UNION ALL SELECT 'tat_nav_pose_master',   COUNT(*) FROM tat_nav_pose_master
UNION ALL SELECT 'ai_model',             COUNT(*) FROM ai_model
UNION ALL SELECT 'ra_motion_step',       COUNT(*) FROM ra_motion_step
ORDER BY table_name;
