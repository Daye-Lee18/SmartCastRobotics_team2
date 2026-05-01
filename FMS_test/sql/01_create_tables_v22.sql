-- =============================================
-- PostgreSQL DDL - create_tables_v22.sql
-- SmartCast DB Schema v22 (Consolidated)
-- =============================================

-- =====================
-- USER
-- =====================

CREATE TABLE user_account (
    user_id   SERIAL   PRIMARY KEY,
    co_nm     VARCHAR  NOT NULL,
    user_nm   VARCHAR  NOT NULL,
    role      VARCHAR  CHECK (role IN ('customer', 'admin', 'operator', 'fms')),
    phone     VARCHAR,
    email     VARCHAR  NOT NULL UNIQUE,
    password  VARCHAR  NOT NULL
);

-- =====================
-- ADMIN / MASTER
-- =====================

CREATE TABLE category (
    cate_cd  VARCHAR  PRIMARY KEY CHECK (cate_cd IN ('CMH', 'RMH', 'EMH')),
    cate_nm  VARCHAR  NOT NULL UNIQUE
);

CREATE TABLE product (
    prod_id     SERIAL        PRIMARY KEY,
    cate_cd     VARCHAR       NOT NULL REFERENCES category(cate_cd),
    base_price  DECIMAL       NOT NULL,
    img_url     VARCHAR(400)
);

CREATE TABLE product_option (
    prod_opt_id  SERIAL       PRIMARY KEY,
    prod_id      INT          NOT NULL REFERENCES product(prod_id),
    mat_type     VARCHAR(20)  NOT NULL,
    diameter     DECIMAL      NOT NULL,
    thickness    DECIMAL      NOT NULL,
    material     VARCHAR(30)  NOT NULL,
    load_class   VARCHAR(20)  NOT NULL
);

CREATE TABLE pp_options (
    pp_id       SERIAL   PRIMARY KEY,
    pp_nm       VARCHAR  NOT NULL UNIQUE,
    extra_cost  DECIMAL  DEFAULT 0
);

CREATE TABLE flow_stat_cd (
    flow_stat  VARCHAR(20)  PRIMARY KEY
);

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
('HOLD');

-- =====================
-- RESOURCE MASTER
-- =====================

CREATE TABLE res (
    res_id    VARCHAR(10)  PRIMARY KEY,  -- RA1, RA2, RA3, CONV1, AMR1...
    res_type  VARCHAR      NOT NULL CHECK (res_type IN ('RA', 'CONV', 'AMR')),
    model_nm  VARCHAR      NOT NULL
);

CREATE TABLE zone (
    zone_id  SERIAL   PRIMARY KEY,
    zone_nm  VARCHAR  NOT NULL UNIQUE
        CHECK (zone_nm IN ('CAST', 'PP', 'INSP', 'STRG', 'PICK', 'SHIP', 'CHG'))
);

CREATE TABLE equip (
    res_id   VARCHAR(10)  PRIMARY KEY REFERENCES res(res_id),
    zone_id  INT          REFERENCES zone(zone_id)
);

CREATE TABLE equip_load_spec (
    load_spec_id  SERIAL         PRIMARY KEY,
    load_class    VARCHAR(20),
    press_f       DECIMAL(10,2),
    press_t       DECIMAL(5,2),
    tol_val       DECIMAL(5,2)
);

-- =====================
-- ORDER
-- =====================

CREATE TABLE ord (
    ord_id      SERIAL     PRIMARY KEY,
    user_id     INT        NOT NULL REFERENCES user_account(user_id),
    created_at  TIMESTAMP  DEFAULT now()
);

CREATE TABLE ord_detail (
    ord_id       INT      PRIMARY KEY REFERENCES ord(ord_id),
    prod_id      INT      REFERENCES product(prod_id),
    qty          INT      NOT NULL CHECK (qty > 0),
    final_price  DECIMAL  NOT NULL,
    due_date     DATE     NOT NULL,
    ship_addr    VARCHAR  NOT NULL
);

CREATE TABLE ord_pp_map (
    map_id  SERIAL  PRIMARY KEY,
    ord_id  INT     NOT NULL REFERENCES ord(ord_id),
    pp_id   INT     NOT NULL REFERENCES pp_options(pp_id),
    UNIQUE (ord_id, pp_id)
);

CREATE TABLE ord_txn (
    txn_id    SERIAL     PRIMARY KEY,
    ord_id    INT        NOT NULL REFERENCES ord(ord_id),
    txn_type  VARCHAR    NOT NULL DEFAULT 'RCVD'
        CHECK (txn_type IN ('RCVD', 'APPR', 'CNCL', 'REJT')),
    txn_at    TIMESTAMP  DEFAULT now()
);

CREATE TABLE ord_stat (
    stat_id     SERIAL     PRIMARY KEY,
    ord_id      INT        NOT NULL UNIQUE REFERENCES ord(ord_id),
    user_id     INT        REFERENCES user_account(user_id),
    ord_stat    VARCHAR    NOT NULL
        CHECK (ord_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIPPING', 'COMP', 'REJT', 'CNCL')),
    gp_qty      INT        NOT NULL DEFAULT 0 CHECK (gp_qty >= 0),
    dp_qty      INT        NOT NULL DEFAULT 0 CHECK (dp_qty >= 0),
    updated_at  TIMESTAMP  DEFAULT now()
);

CREATE TABLE ord_log (
    log_id      SERIAL     PRIMARY KEY,
    ord_id      INT        NOT NULL REFERENCES ord(ord_id),
    prev_stat   VARCHAR    CHECK (prev_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIPPING', 'COMP', 'REJT', 'CNCL')),
    new_stat    VARCHAR    NOT NULL CHECK (new_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIPPING', 'COMP', 'REJT', 'CNCL')),
    changed_by  INT        REFERENCES user_account(user_id),
    logged_at   TIMESTAMP  DEFAULT now()
);

-- =====================
-- ITEM STATE
-- =====================

CREATE TABLE item_stat (
    item_stat_id  SERIAL      PRIMARY KEY,
    ord_id        INT         NOT NULL REFERENCES ord(ord_id),
    flow_stat     VARCHAR(20) NOT NULL REFERENCES flow_stat_cd(flow_stat),
    res_id        VARCHAR(10) REFERENCES res(res_id),
    zone_nm       VARCHAR(20) REFERENCES zone(zone_nm),
    result        BOOLEAN,    -- NULL=미검사, TRUE=GP, FALSE=DP. 원천 결과는 insp_stat.final_result.
    updated_at    TIMESTAMP   DEFAULT now()
);

CREATE INDEX idx_item_stat_ord_flow ON item_stat (ord_id, flow_stat);

-- =====================
-- PICK (Moved up to avoid ALTER TABLE on equip_task_txn)
-- =====================

CREATE TABLE pick_txn (
    txn_id      SERIAL       PRIMARY KEY,
    ord_id      INT          NOT NULL REFERENCES ord(ord_id),
    txn_stat    VARCHAR(10)  NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    req_qty     INT          NOT NULL,
    picked_qty  INT          NOT NULL DEFAULT 0,
    req_at      TIMESTAMP    DEFAULT now(),
    start_at    TIMESTAMP,
    end_at      TIMESTAMP,
    CONSTRAINT chk_pick_qty CHECK (
        req_qty > 0
        AND picked_qty >= 0
        AND picked_qty <= req_qty
    )
);

-- =====================
-- OPERATOR / COORD / LOCATION STATE
-- =====================

CREATE TABLE pattern_stat (
    ptn_id         INT       PRIMARY KEY REFERENCES ord(ord_id),
    ptn_loc        INT       NOT NULL CHECK (ptn_loc BETWEEN 1 AND 6),
    registered_by  INT       REFERENCES user_account(user_id),
    created_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE chg_loc_stat (
    loc_id          SERIAL     PRIMARY KEY,
    zone_id         INT        REFERENCES zone(zone_id),
    trans_coord_id  INT,       -- FK added after trans_coord because of circular dependency.
    res_id          VARCHAR    REFERENCES res(res_id),
    loc_row         INT,
    loc_col         INT,
    status          VARCHAR    NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at       TIMESTAMP  DEFAULT now(),
    CONSTRAINT chk_chg_res_status CHECK (
        (res_id IS NOT NULL AND status = 'occupied') OR
        (res_id IS NULL     AND status IN ('empty', 'reserved'))
    )
);

CREATE TABLE trans_coord (
    trans_coord_id  SERIAL   PRIMARY KEY,
    zone_id         INT      NOT NULL REFERENCES zone(zone_id),
    chg_loc_id      INT      REFERENCES chg_loc_stat(loc_id),
    x               DECIMAL  NOT NULL,
    y               DECIMAL  NOT NULL,
    theta           DECIMAL  NOT NULL,
    UNIQUE (zone_id, chg_loc_id)
);

-- Circular dependency for trans_coord ↔ chg_loc_stat still needs one ALTER TABLE or deferred constraint.
-- Given the "no alter table" request, I will keep this one if it's the only way, 
-- or use a deferred constraint if supported in the target environment.
-- But the user likely wants to avoid the ones I CAN avoid by ordering.
ALTER TABLE chg_loc_stat
    ADD CONSTRAINT fk_chg_loc_trans_coord
    FOREIGN KEY (trans_coord_id) REFERENCES trans_coord(trans_coord_id);

CREATE TABLE strg_loc_stat (
    loc_id        SERIAL     PRIMARY KEY,
    zone_id       INT        REFERENCES zone(zone_id),
    item_stat_id  INT        REFERENCES item_stat(item_stat_id),
    loc_row       INT,
    loc_col       INT,
    status        VARCHAR    NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at     TIMESTAMP  DEFAULT now(),
    CONSTRAINT chk_strg_item_stat_status CHECK (
        (item_stat_id IS NOT NULL AND status = 'occupied') OR
        (item_stat_id IS NULL     AND status IN ('empty', 'reserved'))
    )
);

CREATE TABLE ship_loc_stat (
    loc_id        SERIAL     PRIMARY KEY,
    zone_id       INT        REFERENCES zone(zone_id),
    ord_id        INT        REFERENCES ord(ord_id),
    item_stat_id  INT        REFERENCES item_stat(item_stat_id),
    loc_row       INT,
    loc_col       INT,
    status        VARCHAR    NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at     TIMESTAMP  DEFAULT now(),
    CONSTRAINT chk_ship_item_stat_status CHECK (
        (item_stat_id IS NOT NULL AND status = 'occupied') OR
        (item_stat_id IS NULL     AND status IN ('empty', 'reserved'))
    )
);

-- Unified RA motion sequence.
CREATE TABLE ra_motion_step (
    step_id       SERIAL   PRIMARY KEY,
    task_type     VARCHAR  NOT NULL CHECK (task_type IN (
        'MM', 'POUR', 'DM', 'PA_GP', 'PA_DP', 'PICK', 'SHIP'
    )),
    pattern_no    INT      CHECK (pattern_no BETWEEN 1 AND 6),
    loc_id        INT      REFERENCES strg_loc_stat(loc_id),
    pose_nm       VARCHAR  CHECK (pose_nm IN (
        'HOME', 'AMR_HANDOFF', 'DEFECT_HOVER', 'DEFECT_DROP', 'SLOT_PATH'
    )),
    step_ord      INT      NOT NULL,
    command_type  VARCHAR  NOT NULL CHECK (command_type IN (
        'MOVE_ANGLES', 'MOVE_Z', 'GRIP_OPEN', 'GRIP_CLOSE', 'WAIT'
    )),
    j1            DECIMAL,
    j2            DECIMAL,
    j3            DECIMAL,
    j4            DECIMAL,
    j5            DECIMAL,
    j6            DECIMAL,
    delta_z       DECIMAL,
    speed         INT,
    delay_sec     DECIMAL,
    CONSTRAINT chk_cast_ra_step_payload CHECK (
        (
            command_type = 'MOVE_ANGLES'
            AND j1 IS NOT NULL AND j2 IS NOT NULL AND j3 IS NOT NULL
            AND j4 IS NOT NULL AND j5 IS NOT NULL AND j6 IS NOT NULL
            AND delta_z IS NULL
        )
        OR (
            command_type = 'MOVE_Z'
            AND delta_z IS NOT NULL
            AND j1 IS NULL AND j2 IS NULL AND j3 IS NULL
            AND j4 IS NULL AND j5 IS NULL AND j6 IS NULL
        )
        OR (
            command_type IN ('GRIP_OPEN', 'GRIP_CLOSE', 'WAIT')
            AND delta_z IS NULL
            AND j1 IS NULL AND j2 IS NULL AND j3 IS NULL
            AND j4 IS NULL AND j5 IS NULL AND j6 IS NULL
        )
    ),
    CONSTRAINT chk_ra_motion_context CHECK (
        (task_type = 'MM' AND pattern_no IS NOT NULL AND loc_id IS NULL)
        OR
        (task_type IN ('POUR', 'DM', 'PA_DP') AND pattern_no IS NULL)
        OR
        (task_type IN ('PA_GP', 'PICK', 'SHIP') AND pattern_no IS NULL AND loc_id IS NOT NULL)
    ),
    UNIQUE NULLS NOT DISTINCT (task_type, pattern_no, loc_id, pose_nm, step_ord)
);

CREATE TABLE pp_task_txn (
    txn_id        SERIAL     PRIMARY KEY,
    ord_id        INT        NOT NULL REFERENCES ord(ord_id),
    item_stat_id  INT        REFERENCES item_stat(item_stat_id),
    map_id        INT        REFERENCES ord_pp_map(map_id),
    pp_nm         VARCHAR    REFERENCES pp_options(pp_nm),
    operator_id   INT        REFERENCES user_account(user_id),
    txn_stat      VARCHAR    NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    req_at        TIMESTAMP  DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP
);

-- =====================
-- EQUIPMENT TASK / STATE
-- =====================

CREATE TABLE equip_task_txn (
    txn_id        SERIAL       PRIMARY KEY,
    res_id        VARCHAR(10)  REFERENCES equip(res_id),
    task_type     VARCHAR      NOT NULL
        CHECK (task_type IN (
            'MM', 'POUR', 'DM', 'PP',
            'PA_GP', 'PA_DP', 'PICK', 'SHIP',
            'ToINSP', 'ToPAWait'
        )),
    txn_stat      VARCHAR      NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    item_stat_id  INT          REFERENCES item_stat(item_stat_id),
    ord_id        INT          REFERENCES ord(ord_id),
    strg_loc_id   INT          REFERENCES strg_loc_stat(loc_id),
    ship_loc_id   INT          REFERENCES ship_loc_stat(loc_id),
    pick_txn_id   INT          REFERENCES pick_txn(txn_id), -- Included here, no ALTER TABLE
    req_at        TIMESTAMP    DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP
);

CREATE TABLE equip_stat (
    stat_id       SERIAL       PRIMARY KEY,
    res_id        VARCHAR(10)  NOT NULL UNIQUE REFERENCES equip(res_id),
    item_stat_id  INT          REFERENCES item_stat(item_stat_id),
    txn_type      VARCHAR,
    cur_stat      VARCHAR      CHECK (cur_stat IN (
        'IDLE', 'ALLOC', 'FAIL',
        'MV_SRC', 'GRASP', 'MV_DEST', 'RELEASE', 'TO_IDLE',
        'ON', 'OFF'
    )),
    updated_at    TIMESTAMP    DEFAULT now(),
    err_msg       VARCHAR
);

-- =====================
-- TRANSPORT TASK / STATE
-- =====================

CREATE TABLE trans (
    res_id         VARCHAR(10)  PRIMARY KEY REFERENCES res(res_id),
    slot_count     INT          CHECK (slot_count > 0),
    max_load_kg    NUMERIC,
    home_coord_id  INT          REFERENCES trans_coord(trans_coord_id)
);

CREATE TABLE trans_task_bat_threshold (
    res_id             VARCHAR(10)  REFERENCES trans(res_id),
    task_type          VARCHAR(10)  CHECK (task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')),
    bat_low_threshold  INT          CHECK (bat_low_threshold >= 0 AND bat_low_threshold <= 100),
    PRIMARY KEY (res_id, task_type)
);

CREATE TABLE trans_task_txn (
    txn_id        SERIAL       PRIMARY KEY,
    res_id        VARCHAR(10)  REFERENCES trans(res_id),
    task_type     VARCHAR      NOT NULL CHECK (task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')),
    txn_stat      VARCHAR      NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    chg_loc_id    INT          REFERENCES trans_coord(trans_coord_id),
    item_stat_id  INT          REFERENCES item_stat(item_stat_id),
    ord_id        INT          REFERENCES ord(ord_id),
    req_at        TIMESTAMP    DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP
);

CREATE TABLE trans_stat (
    res_id              VARCHAR(10)  PRIMARY KEY REFERENCES trans(res_id),
    item_stat_id        INT          REFERENCES item_stat(item_stat_id),
    cur_stat            VARCHAR      CHECK (cur_stat IN (
        'IDLE', 'ALLOC', 'CHG', 'TO_IDLE',
        'MV_SRC', 'WAIT_LD', 'MV_DEST', 'WAIT_DLD',
        'SUCC', 'FAIL'
    )),
    battery_pct         INT          CHECK (battery_pct >= 0 AND battery_pct <= 100),
    cur_trans_coord_id  INT          REFERENCES trans_coord(trans_coord_id),
    updated_at          TIMESTAMP    DEFAULT now()
);

-- =====================
-- ITEM TRANSACTION (from item_txn_table.sql)
-- =====================

CREATE TABLE item_txn (
    txn_id        SERIAL       PRIMARY KEY,
    item_stat_id  INT          NOT NULL REFERENCES item_stat(item_stat_id),
    ord_id        INT          REFERENCES ord(ord_id),

    -- item이 이 txn 시점에 속한 flow 단계
    flow_stat     VARCHAR(20)  NOT NULL REFERENCES flow_stat_cd(flow_stat),

    -- actor 구분: EQUIP(RA/CONV) / TRANS(AMR) / AI / HUMAN
    actor_type    VARCHAR(10)  NOT NULL
        CHECK (actor_type IN ('EQUIP', 'TRANS', 'AI', 'HUMAN')),

    -- EQUIP / TRANS / AI → res_id 필수, user_id NULL
    -- HUMAN             → user_id 필수, res_id NULL
    res_id        VARCHAR(10)  REFERENCES res(res_id),
    user_id       INT          REFERENCES user_account(user_id),

    task_type     VARCHAR(20)  NOT NULL,

    txn_stat      VARCHAR(10)  NOT NULL
        CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),

    -- 원본 txn 테이블 역참조
    -- SQL FK는 단일 테이블만 가능 → 논리 포인터로 처리
    ref_txn_type  VARCHAR(20)
        CHECK (ref_txn_type IN (
            'equip_task_txn',
            'trans_task_txn',
            'insp_task_txn',
            'pp_task_txn',
            'ai_inference_txn'
        )),
    ref_txn_id    INT,

    req_at        TIMESTAMP    DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP,

    -- actor_type별 필수 컬럼 강제
    CONSTRAINT chk_item_txn_actor CHECK (
        (actor_type IN ('EQUIP', 'TRANS', 'AI')
            AND res_id  IS NOT NULL
            AND user_id IS NULL)
        OR
        (actor_type = 'HUMAN'
            AND user_id IS NOT NULL
            AND res_id  IS NULL)
    )
);

CREATE INDEX idx_item_txn_item_stat  ON item_txn (item_stat_id, txn_stat);
CREATE INDEX idx_item_txn_ord        ON item_txn (ord_id);
CREATE INDEX idx_item_txn_flow_stat  ON item_txn (flow_stat);

-- =====================
-- AI MODEL / INSPECTION
-- =====================

CREATE TABLE ai_model (
    model_id      SERIAL       PRIMARY KEY,
    model_nm      VARCHAR(50)  NOT NULL,
    model_type    VARCHAR(20)  NOT NULL CHECK (model_type IN ('YOLO', 'PATCHCORE')),
    target_cls    VARCHAR(5)   CHECK (target_cls IN ('CMH', 'RMH', 'EMH')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    DEFAULT now(),
    CONSTRAINT chk_patchcore_target_class CHECK (
        (model_type = 'YOLO' AND target_cls IS NULL) OR
        (model_type = 'PATCHCORE' AND target_cls IS NOT NULL)
    ),
    UNIQUE (model_nm, model_type, target_cls)
);

CREATE TABLE insp_task_txn (
    txn_id        SERIAL       PRIMARY KEY,
    item_stat_id  INT          NOT NULL REFERENCES item_stat(item_stat_id),
    txn_stat      VARCHAR(10)  NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    res_id        VARCHAR(10)  REFERENCES equip(res_id),
    req_at        TIMESTAMP    DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP
);

CREATE TABLE ai_inference_txn (
    inference_id  SERIAL       PRIMARY KEY,
    insp_txn_id   INT          NOT NULL REFERENCES insp_task_txn(txn_id),
    model_id      INT          NOT NULL REFERENCES ai_model(model_id),
    step_type     VARCHAR(30)  NOT NULL CHECK (step_type IN ('CLASSIFICATION', 'ANOMALY_DETECTION')),
    txn_stat      VARCHAR(10)  NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    req_at        TIMESTAMP    DEFAULT now(),
    start_at      TIMESTAMP,
    end_at        TIMESTAMP
);

CREATE TABLE insp_stat (
    insp_txn_id             INT        PRIMARY KEY REFERENCES insp_task_txn(txn_id),
    item_stat_id            INT        NOT NULL REFERENCES item_stat(item_stat_id),
    yolo_inference_id       INT        REFERENCES ai_inference_txn(inference_id),
    patchcore_inference_id  INT        REFERENCES ai_inference_txn(inference_id),
    predicted_class         VARCHAR(5) CHECK (predicted_class IN ('CMH', 'RMH', 'EMH')),
    yolo_confidence         NUMERIC,
    anomaly_score           NUMERIC,
    anomaly_threshold       NUMERIC,
    final_result            VARCHAR(2) CHECK (final_result IN ('GP', 'DP')),
    result_json             JSONB,
    updated_at              TIMESTAMP  DEFAULT now()
);

-- =====================
-- PICK ITEM MAP
-- =====================

CREATE TABLE pick_item_map (
    pick_txn_id   INT          NOT NULL REFERENCES pick_txn(txn_id),
    item_stat_id  INT          NOT NULL REFERENCES item_stat(item_stat_id),
    equip_txn_id  INT          REFERENCES equip_task_txn(txn_id),
    pick_stat     VARCHAR(10)  NOT NULL CHECK (pick_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    mapped_at     TIMESTAMP    DEFAULT now(),
    PRIMARY KEY (pick_txn_id, item_stat_id)
);

-- =====================
-- PICK READY TRIGGER
-- =====================

-- PICK can start only when ord_stat.gp_qty equals ord_detail.qty.
CREATE OR REPLACE FUNCTION validate_pick_ready()
RETURNS trigger AS $$
DECLARE
    v_qty INT;
    v_gp_qty INT;
BEGIN
    SELECT od.qty, os.gp_qty
      INTO v_qty, v_gp_qty
      FROM ord_detail od
      JOIN ord_stat os ON os.ord_id = od.ord_id
     WHERE od.ord_id = NEW.ord_id;

    IF v_qty IS NULL THEN
        RAISE EXCEPTION 'Cannot create pick_txn: ord_id % has no ord_detail/ord_stat row', NEW.ord_id;
    END IF;

    IF v_gp_qty <> v_qty THEN
        RAISE EXCEPTION 'Cannot create pick_txn: ord_id %, gp_qty % does not equal qty %',
            NEW.ord_id, v_gp_qty, v_qty;
    END IF;

    IF NEW.req_qty <> v_qty THEN
        RAISE EXCEPTION 'Cannot create pick_txn: req_qty % does not equal ord_detail.qty %',
            NEW.req_qty, v_qty;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_pick_ready
BEFORE INSERT OR UPDATE OF ord_id, req_qty ON pick_txn
FOR EACH ROW
EXECUTE FUNCTION validate_pick_ready();

-- =====================
-- ALERTS
-- =====================

CREATE TABLE alerts_stat (
    id              VARCHAR       PRIMARY KEY,
    res_id          VARCHAR(10)   NOT NULL REFERENCES res(res_id),
    type            VARCHAR       NOT NULL,
    severity        VARCHAR       NOT NULL DEFAULT 'info'
        CHECK (severity IN ('info', 'warning', 'critical')),
    error_code      VARCHAR       DEFAULT '',
    message         VARCHAR       NOT NULL,
    abnormal_value  VARCHAR       DEFAULT '',
    zone            VARCHAR,
    "timestamp"     VARCHAR       NOT NULL,
    resolved_at     VARCHAR,
    acknowledged    BOOLEAN       NOT NULL DEFAULT FALSE
);

-- =====================
-- LOG TABLES
-- =====================

CREATE TABLE log_action_user (
    log_id       SERIAL       PRIMARY KEY,
    user_id      INT          NOT NULL REFERENCES user_account(user_id),
    screen_nm    VARCHAR(50)  NOT NULL,
    action_type  VARCHAR(50)  NOT NULL,
    ref_id       INT,
    acted_at     TIMESTAMP    DEFAULT now()
);

CREATE TABLE log_action_operator_handoff_acks (
    log_id            SERIAL    PRIMARY KEY,
    operator_id       INT       NOT NULL REFERENCES user_account(user_id),
    item_stat_id      INT       REFERENCES item_stat(item_stat_id),
    pp_task_txn_id    INT       REFERENCES pp_task_txn(txn_id),
    button_device_id  VARCHAR,
    idempotency_key   VARCHAR   UNIQUE,
    ack_at            TIMESTAMP DEFAULT now()
);

CREATE TABLE log_action_operator_rfid_scan (
    id               BIGSERIAL     NOT NULL,
    scanned_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    reader_id        VARCHAR       NOT NULL,
    zone             VARCHAR,
    raw_payload      VARCHAR       NOT NULL,
    ord_id           VARCHAR,
    item_key         VARCHAR,
    item_stat_id     INT           REFERENCES item_stat(item_stat_id),
    parse_status     VARCHAR       NOT NULL CHECK (parse_status IN ('ok', 'bad_format', 'duplicate')),
    idempotency_key  VARCHAR,
    metadata         JSONB,
    PRIMARY KEY (id, scanned_at)
);

CREATE UNIQUE INDEX uq_rfid_scan_idempotency_key
    ON log_action_operator_rfid_scan (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE log_action_admin (
    log_id        SERIAL       PRIMARY KEY,
    admin_id      INT          NOT NULL REFERENCES user_account(user_id),
    target_table  VARCHAR(50)  NOT NULL,
    target_id     VARCHAR(50),
    action_type   VARCHAR(10)  CHECK (action_type IN ('INSERT', 'UPDATE', 'DELETE')),
    old_value     JSONB,
    new_value     JSONB,
    acted_at      TIMESTAMP    DEFAULT now()
);

CREATE TABLE log_event (
    log_id      SERIAL       PRIMARY KEY,
    component   VARCHAR(20)  NOT NULL,
    event_type  VARCHAR(50)  NOT NULL,
    txn_id      INT,
    detail      TEXT,
    occured_at  TIMESTAMP    DEFAULT now()
);

CREATE TABLE log_data_equip (
    log_id          SERIAL        PRIMARY KEY,
    res_id          VARCHAR(10)   NOT NULL REFERENCES res(res_id),
    txn_id          INT           REFERENCES equip_task_txn(txn_id),
    sensor_type     VARCHAR(30)   NOT NULL,
    raw_value       DECIMAL(10,4) NOT NULL,
    physical_value  DECIMAL(10,4),
    unit            VARCHAR(10),
    status          VARCHAR(10)   CHECK (status IN ('normal', 'warning', 'fault')),
    logged_at       TIMESTAMP     DEFAULT now()
);

CREATE TABLE log_data_trans (
    log_id          SERIAL        PRIMARY KEY,
    res_id          VARCHAR(10)   NOT NULL REFERENCES res(res_id),
    txn_id          INT           REFERENCES trans_task_txn(txn_id),
    sensor_type     VARCHAR(30)   NOT NULL,
    raw_value       DECIMAL(10,4) NOT NULL,
    physical_value  DECIMAL(10,4),
    unit            VARCHAR(10),
    status          VARCHAR(10)   CHECK (status IN ('normal', 'warning', 'fault')),
    logged_at       TIMESTAMP     DEFAULT now()
);

CREATE TABLE log_err_equip (
    err_id       SERIAL       PRIMARY KEY,
    res_id       VARCHAR(10)  REFERENCES res(res_id),
    task_txn_id  INT          REFERENCES equip_task_txn(txn_id),
    failed_stat  VARCHAR,
    err_msg      VARCHAR,
    occured_at   TIMESTAMP    DEFAULT now()
);

CREATE TABLE log_err_trans (
    err_id       SERIAL       PRIMARY KEY,
    res_id       VARCHAR(10)  REFERENCES res(res_id),
    task_txn_id  INT          REFERENCES trans_task_txn(txn_id),
    failed_stat  VARCHAR,
    err_msg      VARCHAR,
    battery_pct  INT,
    occured_at   TIMESTAMP    DEFAULT now()
);
