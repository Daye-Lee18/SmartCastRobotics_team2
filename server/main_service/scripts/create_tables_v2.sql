-- =============================================
-- PostgreSQL DDL — create_tables_v2.sql
-- Source: Confluence page 32342045 (DB Schema and ERD v59, 2026-04-18)
--   https://dayelee313.atlassian.net/wiki/spaces/addinedute/pages/32342045
-- Target: PostgreSQL 16 / schema 'smartcast' (within smartcast_robotics DB)
-- Author: 이다예 (owner) / 적용: 김기수
-- 적용일: 2026-04-19
--
-- 주의:
--   1. 본 스크립트는 idempotent하지 않다 (CREATE TABLE만 사용).
--      재적용 전 DROP SCHEMA smartcast CASCADE 필요.
--   2. team2 role은 CREATEDB 권한 없음 → 별도 DB 대신 schema 'smartcast' 사용.
--   3. ord/item/res/equip 테이블은 책임 분리 패턴 (master + transaction + stat + log).
-- =============================================

-- 신규 schema 사용
SET search_path TO smartcast, public;

-- =====================
-- USER
-- =====================

CREATE TABLE smartcast.user_account (
    user_id   SERIAL       PRIMARY KEY,
    co_nm     VARCHAR      NOT NULL,
    user_nm   VARCHAR      NOT NULL,
    role      VARCHAR      CHECK (role IN ('customer', 'admin', 'operator', 'fms')),
    phone     VARCHAR,
    email     VARCHAR      NOT NULL UNIQUE,
    password  VARCHAR
);

-- =====================
-- ORDER (master)
-- =====================

CREATE TABLE smartcast.ord (
    ord_id      SERIAL    PRIMARY KEY,
    user_id     INT       NOT NULL REFERENCES smartcast.user_account(user_id),
    created_at  TIMESTAMP DEFAULT now()
);

-- =====================
-- ADMIN (product 마스터들 — ord_detail이 product를 참조하므로 먼저 생성)
-- =====================

CREATE TABLE smartcast.category (
    cate_cd  VARCHAR  PRIMARY KEY CHECK (cate_cd IN ('CMH', 'RMH', 'EMH')),
    cate_nm  VARCHAR  NOT NULL UNIQUE
);

CREATE TABLE smartcast.product (
    prod_id     SERIAL        PRIMARY KEY,
    cate_cd     VARCHAR       NOT NULL REFERENCES smartcast.category(cate_cd),
    base_price  DECIMAL       NOT NULL,
    img_url     VARCHAR(400)
);

CREATE TABLE smartcast.product_option (
    prod_opt_id  SERIAL       PRIMARY KEY,
    prod_id      INT          NOT NULL REFERENCES smartcast.product(prod_id),
    mat_type     VARCHAR(20),
    load_class   VARCHAR(20)
);

CREATE TABLE smartcast.pp_options (
    pp_id       SERIAL   PRIMARY KEY,
    pp_nm       VARCHAR  UNIQUE,
    extra_cost  DECIMAL
);

CREATE TABLE smartcast.ord_detail (
    ord_id       INT           PRIMARY KEY REFERENCES smartcast.ord(ord_id),
    prod_id      INT           REFERENCES smartcast.product(prod_id),
    diameter     DECIMAL,
    thickness    DECIMAL,
    material     VARCHAR(30),
    load_class   VARCHAR(20),
    qty          INT,
    final_price  DECIMAL,
    due_date     DATE,
    ship_addr    VARCHAR
);

CREATE TABLE smartcast.ord_pp_map (
    map_id  SERIAL  PRIMARY KEY,
    ord_id  INT     NOT NULL REFERENCES smartcast.ord(ord_id),
    pp_id   INT     NOT NULL REFERENCES smartcast.pp_options(pp_id)
);

CREATE TABLE smartcast.ord_txn (
    txn_id    SERIAL    PRIMARY KEY,
    ord_id    INT       NOT NULL REFERENCES smartcast.ord(ord_id),
    txn_type  VARCHAR   DEFAULT 'RCVD' CHECK (txn_type IN ('RCVD', 'APPR', 'CNCL', 'REJT')),
    txn_at    TIMESTAMP DEFAULT now()
);

-- =====================
-- OPERATOR (zone, pattern 등)
-- =====================

CREATE TABLE smartcast.zone (
    zone_id  SERIAL   PRIMARY KEY,
    zone_nm  VARCHAR  UNIQUE CHECK (zone_nm IN ('CAST', 'PP', 'INSP', 'STRG', 'SHIP', 'CHG'))
);

CREATE TABLE smartcast.pattern (
    ptn_id   INT  PRIMARY KEY REFERENCES smartcast.ord(ord_id),
    ptn_loc  INT  CHECK (ptn_loc BETWEEN 1 AND 6)
);

-- =====================
-- 설비 Master (res, equip)
-- =====================

CREATE TABLE smartcast.res (
    res_id    VARCHAR(10)  PRIMARY KEY,
    res_type  VARCHAR      CHECK (res_type IN ('RA', 'CONV', 'AMR')),
    model_nm  VARCHAR      NOT NULL
);

CREATE TABLE smartcast.equip (
    res_id   VARCHAR(10)  PRIMARY KEY REFERENCES smartcast.res(res_id),
    zone_id  INT          REFERENCES smartcast.zone(zone_id)
);

CREATE TABLE smartcast.equip_load_spec (
    load_spec_id  SERIAL         PRIMARY KEY,
    load_class    VARCHAR(20),
    press_f       DECIMAL(10,2),
    press_t       DECIMAL(5,2),
    tol_val       DECIMAL(5,2)
);

-- =====================
-- FMS — item (res 참조하므로 res 다음에 생성)
-- =====================

CREATE TABLE smartcast.item (
    item_id          SERIAL        PRIMARY KEY,
    ord_id           INT           NOT NULL REFERENCES smartcast.ord(ord_id),
    equip_task_type  VARCHAR(10),
    trans_task_type  VARCHAR(10),
    cur_stat         VARCHAR(10),
    cur_res          VARCHAR(10)   REFERENCES smartcast.res(res_id),
    is_defective     BOOLEAN,
    updated_at       TIMESTAMP     DEFAULT now()
);

-- =====================
-- OPERATOR (location stat — item, res 참조)
-- =====================

CREATE TABLE smartcast.chg_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES smartcast.zone(zone_id),
    res_id    VARCHAR   REFERENCES smartcast.res(res_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now()
);

CREATE TABLE smartcast.strg_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES smartcast.zone(zone_id),
    item_id   INT       REFERENCES smartcast.item(item_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now(),
    CONSTRAINT chk_strg_item_status CHECK (
        (item_id IS NOT NULL AND status = 'occupied') OR
        (item_id IS NULL     AND status IN ('empty', 'reserved'))
    )
);

CREATE TABLE smartcast.ship_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES smartcast.zone(zone_id),
    ord_id    INT       REFERENCES smartcast.ord(ord_id),
    item_id   INT       REFERENCES smartcast.item(item_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now()
);

-- =====================
-- FMS (ord_stat, ord_log)
-- =====================

CREATE TABLE smartcast.ord_stat (
    stat_id     SERIAL    PRIMARY KEY,
    ord_id      INT       NOT NULL REFERENCES smartcast.ord(ord_id),
    user_id     INT       REFERENCES smartcast.user_account(user_id),
    ord_stat    VARCHAR   CHECK (ord_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    updated_at  TIMESTAMP DEFAULT now()
);

CREATE TABLE smartcast.ord_log (
    log_id      SERIAL    PRIMARY KEY,
    ord_id      INT       NOT NULL REFERENCES smartcast.ord(ord_id),
    prev_stat   VARCHAR   CHECK (prev_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    new_stat    VARCHAR   CHECK (new_stat  IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    changed_by  INT       REFERENCES smartcast.user_account(user_id),
    logged_at   TIMESTAMP DEFAULT now()
);

-- =====================
-- OPERATOR — pp_task_txn
-- =====================

CREATE TABLE smartcast.pp_task_txn (
    txn_id       SERIAL    PRIMARY KEY,
    ord_id       INT       NOT NULL REFERENCES smartcast.ord(ord_id),
    map_id       INT       REFERENCES smartcast.ord_pp_map(map_id),
    pp_nm        VARCHAR,
    item_id      INT       REFERENCES smartcast.item(item_id),
    operator_id  INT       REFERENCES smartcast.user_account(user_id),
    txn_stat     VARCHAR   CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    req_at       TIMESTAMP DEFAULT now(),
    start_at     TIMESTAMP,
    end_at       TIMESTAMP
);

-- =====================
-- 생산 설비 — equip_task_txn, equip_stat, equip_err_log
-- =====================

CREATE TABLE smartcast.equip_task_txn (
    txn_id       SERIAL       PRIMARY KEY,
    res_id       VARCHAR(10)  REFERENCES smartcast.res(res_id),
    task_type    VARCHAR,     -- ERR/IDLE/MM/POUR/DM/PP/PA_GP/PA_DP/PICK/SHIP/ToINSP
    txn_stat     VARCHAR      CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    item_id      INT          REFERENCES smartcast.item(item_id),
    strg_loc_id  INT          REFERENCES smartcast.strg_location_stat(loc_id),
    ship_loc_id  INT          REFERENCES smartcast.ship_location_stat(loc_id),
    req_at       TIMESTAMP    DEFAULT now(),
    start_at     TIMESTAMP,
    end_at       TIMESTAMP
);

CREATE TABLE smartcast.equip_stat (
    stat_id     SERIAL       PRIMARY KEY,
    res_id      VARCHAR(10)  NOT NULL REFERENCES smartcast.res(res_id),
    item_id     INT          REFERENCES smartcast.item(item_id),
    txn_type    VARCHAR,
    cur_stat    VARCHAR,     -- RA: MV_SRC/GRASP/MV_DEST/RELEASE/RETURN, CONV: ON/OFF
    updated_at  TIMESTAMP    DEFAULT now(),
    err_msg     VARCHAR
);

CREATE TABLE smartcast.equip_err_log (
    err_id       SERIAL       PRIMARY KEY,
    res_id       VARCHAR(10)  REFERENCES smartcast.res(res_id),
    task_txn_id  INT          REFERENCES smartcast.equip_task_txn(txn_id),
    failed_stat  VARCHAR,
    err_msg      VARCHAR,
    occured_at   TIMESTAMP    DEFAULT now()
);

-- =====================
-- 이동 설비 (Transport / AMR)
-- =====================

CREATE TABLE smartcast.trans (
    res_id       VARCHAR(10)  PRIMARY KEY REFERENCES smartcast.res(res_id),
    slot_count   INT,
    max_load_kg  NUMERIC
);

CREATE TABLE smartcast.trans_task_txn (
    trans_task_txn_id  SERIAL       PRIMARY KEY,
    trans_id           VARCHAR      REFERENCES smartcast.trans(res_id),
    task_type          VARCHAR,     -- ToPP/ToSTRG/ToSHIP/ToCHG
    txn_stat           VARCHAR      CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    chg_loc_id         INT          REFERENCES smartcast.chg_location_stat(loc_id),
    item_id            INT          REFERENCES smartcast.item(item_id),
    ord_id             INT          REFERENCES smartcast.ord(ord_id),
    req_at             TIMESTAMP    DEFAULT now(),
    start_at           TIMESTAMP,
    end_at             TIMESTAMP
);

CREATE TABLE smartcast.trans_stat (
    res_id         VARCHAR   PRIMARY KEY REFERENCES smartcast.trans(res_id),
    item_id        INT       REFERENCES smartcast.item(item_id),
    cur_stat       VARCHAR,
    battery_pct    INT,
    cur_zone_type  VARCHAR,  -- zone.zone_nm 의 값을 저장 (FK 단순화)
    updated_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE smartcast.trans_err_log (
    err_id       SERIAL        PRIMARY KEY,
    res_id       VARCHAR(10)   REFERENCES smartcast.res(res_id),
    task_txn_id  INT           REFERENCES smartcast.trans_task_txn(trans_task_txn_id),
    failed_stat  VARCHAR,
    err_msg      VARCHAR,
    battery_pct  INT,
    occured_at   TIMESTAMP     DEFAULT now()
);

-- =====================
-- 품질 검사 (Inspection)
-- =====================

CREATE TABLE smartcast.insp_task_txn (
    txn_id    SERIAL       PRIMARY KEY,
    item_id   INT          REFERENCES smartcast.item(item_id),
    res_id    VARCHAR(10)  REFERENCES smartcast.res(res_id),
    txn_stat  VARCHAR      CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    result    BOOLEAN,     -- NULL=미검사, FALSE=불량(DP), TRUE=양품(GP)
    req_at    TIMESTAMP    DEFAULT now(),
    start_at  TIMESTAMP,
    end_at    TIMESTAMP
);

-- =====================
-- 자주 쓰는 쿼리용 인덱스
-- =====================

CREATE INDEX IF NOT EXISTS idx_item_ord            ON smartcast.item(ord_id);
CREATE INDEX IF NOT EXISTS idx_item_cur_stat       ON smartcast.item(cur_stat);
CREATE INDEX IF NOT EXISTS idx_equip_task_res      ON smartcast.equip_task_txn(res_id, txn_stat);
CREATE INDEX IF NOT EXISTS idx_trans_task_trans    ON smartcast.trans_task_txn(trans_id, txn_stat);
CREATE INDEX IF NOT EXISTS idx_insp_task_item      ON smartcast.insp_task_txn(item_id);
CREATE INDEX IF NOT EXISTS idx_ord_stat_ord        ON smartcast.ord_stat(ord_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ord_pp_map_ord      ON smartcast.ord_pp_map(ord_id);
CREATE INDEX IF NOT EXISTS idx_pp_task_txn_ord     ON smartcast.pp_task_txn(ord_id, item_id);
CREATE INDEX IF NOT EXISTS idx_ord_txn_ord         ON smartcast.ord_txn(ord_id, txn_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_email          ON smartcast.user_account(email);
