-- ============================================================
-- SmartCast DB Schema
-- Source of truth: server/smart_cast_db/models/
-- ============================================================

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
    password  VARCHAR
);

-- =====================
-- MASTER: PRODUCT
-- =====================

CREATE TABLE category (
    cate_cd  VARCHAR  PRIMARY KEY CHECK (cate_cd IN ('CMH', 'RMH', 'EMH')),
    cate_nm  VARCHAR  NOT NULL UNIQUE
);

CREATE TABLE product (
    prod_id     SERIAL   PRIMARY KEY,
    cate_cd     VARCHAR  NOT NULL REFERENCES category(cate_cd),
    base_price  DECIMAL  NOT NULL,
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

-- =====================
-- MASTER: RESOURCE
-- =====================

CREATE TABLE res (
    res_id    VARCHAR(10)  PRIMARY KEY,
    res_type  VARCHAR      NOT NULL CHECK (res_type IN ('RA', 'CONV', 'TAT')),
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

CREATE TABLE trans (
    res_id       VARCHAR(10)  PRIMARY KEY REFERENCES res(res_id),
    slot_count   INT          CHECK (slot_count > 0),
    max_load_kg  NUMERIC
);

CREATE TABLE trans_task_bat_threshold (
    res_id             VARCHAR(10)  REFERENCES trans(res_id),
    task_type          VARCHAR(10)  CHECK (task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')),
    bat_low_threshold  INT          CHECK (bat_low_threshold >= 0 AND bat_low_threshold <= 100),
    PRIMARY KEY (res_id, task_type)
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
    diameter     DECIMAL,
    thickness    DECIMAL,
    material     VARCHAR(30),
    load_class   VARCHAR(20),
    qty          INT      CHECK (qty > 0),
    final_price  DECIMAL,
    due_date     DATE,
    ship_addr    VARCHAR
);

CREATE TABLE ord_pp_map (
    map_id  SERIAL  PRIMARY KEY,
    ord_id  INT     NOT NULL REFERENCES ord(ord_id),
    pp_id   INT     NOT NULL REFERENCES pp_options(pp_id),
    UNIQUE (ord_id, pp_id)
);

CREATE TABLE pattern_master (
    ptn_id      INT  PRIMARY KEY CHECK (ptn_id BETWEEN 1 AND 3),
    ptn_nm      VARCHAR NOT NULL UNIQUE,
    task_type   VARCHAR NOT NULL CHECK (task_type IN ('MM')),
    description VARCHAR,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE ord_pattern (
    ord_id      INT  PRIMARY KEY REFERENCES ord(ord_id),
    ptn_id      INT  NOT NULL REFERENCES pattern_master(ptn_id),
    assigned_at TIMESTAMP DEFAULT now()
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
    ord_id      INT        NOT NULL REFERENCES ord(ord_id),
    user_id     INT        REFERENCES user_account(user_id),
    ord_stat    VARCHAR    NOT NULL
        CHECK (ord_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    updated_at  TIMESTAMP  DEFAULT now()
);

CREATE TABLE ord_log (
    log_id      SERIAL     PRIMARY KEY,
    ord_id      INT        NOT NULL REFERENCES ord(ord_id),
    prev_stat   VARCHAR    CHECK (prev_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    new_stat    VARCHAR    NOT NULL CHECK (new_stat IN ('RCVD', 'APPR', 'MFG', 'DONE', 'SHIP', 'COMP', 'REJT', 'CNCL')),
    changed_by  INT        REFERENCES user_account(user_id),
    logged_at   TIMESTAMP  DEFAULT now()
);

-- =====================
-- ITEM
-- =====================

CREATE TABLE item (
    item_id          SERIAL       PRIMARY KEY,
    ord_id           INT          NOT NULL REFERENCES ord(ord_id),
    equip_task_type  VARCHAR(10),
    trans_task_type  VARCHAR(10),
    cur_stat         VARCHAR(10),
    cur_res          VARCHAR(10)  REFERENCES res(res_id),
    is_defective     BOOLEAN,
    updated_at       TIMESTAMP    DEFAULT now()
);

CREATE INDEX idx_item_ord ON item (ord_id);

-- =====================
-- LOCATION STATE
-- =====================

CREATE TABLE chg_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES zone(zone_id),
    res_id    VARCHAR   REFERENCES res(res_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now(),
    CONSTRAINT chk_chg_res_status CHECK (
        (res_id IS NOT NULL AND status = 'occupied') OR
        (res_id IS NULL AND status IN ('empty', 'reserved'))
    )
);

CREATE TABLE strg_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES zone(zone_id),
    item_id   INT       REFERENCES item(item_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now(),
    CONSTRAINT chk_strg_item_status CHECK (
        (item_id IS NOT NULL AND status = 'occupied') OR
        (item_id IS NULL AND status IN ('empty', 'reserved'))
    )
);

CREATE TABLE ship_location_stat (
    loc_id    SERIAL    PRIMARY KEY,
    zone_id   INT       REFERENCES zone(zone_id),
    ord_id    INT       REFERENCES ord(ord_id),
    item_id   INT       REFERENCES item(item_id),
    loc_row   INT,
    loc_col   INT,
    status    VARCHAR   NOT NULL CHECK (status IN ('empty', 'occupied', 'reserved')),
    stored_at TIMESTAMP DEFAULT now()
);

CREATE TABLE tat_nav_pose_master (
    pose_id     SERIAL       PRIMARY KEY,
    pose_nm     VARCHAR      NOT NULL UNIQUE CHECK (pose_nm IN (
        'ToINSP', 'ToSHIP', 'ToCAST', 'ToCHG1', 'ToCHG2', 'ToCHG3', 'ToSTRG', 'ToPICK', 'ToPP'
    )),
    zone_id     INT          NOT NULL REFERENCES zone(zone_id),
    loc_id      INT          REFERENCES chg_location_stat(loc_id),
    pose_x      DECIMAL      NOT NULL,
    pose_y      DECIMAL      NOT NULL,
    pose_theta  DECIMAL      NOT NULL,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_tat_nav_pose_chg_loc CHECK (
        (pose_nm LIKE 'ToCHG%' AND loc_id IS NOT NULL)
        OR (pose_nm NOT LIKE 'ToCHG%' AND loc_id IS NULL)
    )
);

-- =====================
-- RA MOTION STEP
-- =====================

CREATE TABLE ra_motion_step (
    step_id       SERIAL   PRIMARY KEY,
    task_type     VARCHAR  NOT NULL CHECK (task_type IN (
        'MM', 'POUR', 'DM', 'PA_GP', 'PA_DP', 'PICK', 'SHIP'
    )),
    tool_type     VARCHAR  NOT NULL DEFAULT 'MAT' CHECK (tool_type IN ('PAT', 'MAT')),
    pattern_no    INT      REFERENCES pattern_master(ptn_id),
    loc_id        INT      REFERENCES strg_location_stat(loc_id),
    pose_nm       VARCHAR  CHECK (pose_nm IN (
        'HOME', 'TAT_HANDOFF', 'DEFECT_HOVER', 'DEFECT_DROP', 'SLOT_PATH'
    )),
    step_ord      INT      NOT NULL,
    command_type  VARCHAR  NOT NULL CHECK (command_type IN (
        'MOVE_ANGLES', 'MOVE_Z', 'GRIP_OPEN', 'GRIP_CLOSE', 'WAIT'
    )),
    j1 DECIMAL, j2 DECIMAL, j3 DECIMAL, j4 DECIMAL, j5 DECIMAL, j6 DECIMAL,
    delta_z   DECIMAL,
    speed     INT,
    delay_sec DECIMAL,
    CONSTRAINT chk_ra_step_payload CHECK (
        (command_type = 'MOVE_ANGLES'
            AND j1 IS NOT NULL AND j2 IS NOT NULL AND j3 IS NOT NULL
            AND j4 IS NOT NULL AND j5 IS NOT NULL AND j6 IS NOT NULL
            AND delta_z IS NULL)
        OR (command_type = 'MOVE_Z'
            AND delta_z IS NOT NULL
            AND j1 IS NULL AND j2 IS NULL AND j3 IS NULL
            AND j4 IS NULL AND j5 IS NULL AND j6 IS NULL)
        OR (command_type IN ('GRIP_OPEN', 'GRIP_CLOSE', 'WAIT')
            AND delta_z IS NULL
            AND j1 IS NULL AND j2 IS NULL AND j3 IS NULL
            AND j4 IS NULL AND j5 IS NULL AND j6 IS NULL)
    ),
    UNIQUE NULLS NOT DISTINCT (task_type, pattern_no, loc_id, pose_nm, step_ord)
);

-- =====================
-- PP TASK
-- =====================

CREATE TABLE pp_task_txn (
    txn_id       SERIAL     PRIMARY KEY,
    ord_id       INT        NOT NULL REFERENCES ord(ord_id),
    item_id      INT        REFERENCES item(item_id),
    map_id       INT        REFERENCES ord_pp_map(map_id),
    pp_nm        VARCHAR    REFERENCES pp_options(pp_nm),
    operator_id  INT        REFERENCES user_account(user_id),
    txn_stat     VARCHAR    NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    req_at       TIMESTAMP  DEFAULT now(),
    start_at     TIMESTAMP,
    end_at       TIMESTAMP
);

-- =====================
-- EQUIPMENT TASK / STATE
-- =====================

CREATE TABLE equip_task_txn (
    txn_id       SERIAL       PRIMARY KEY,
    res_id       VARCHAR(10)  REFERENCES res(res_id),
    task_type    VARCHAR      NOT NULL CHECK (task_type IN (
        'MM', 'POUR', 'DM', 'PP', 'PA_GP', 'PA_DP', 'PICK', 'SHIP', 'ToINSP', 'ToPAWait'
    )),
    txn_stat     VARCHAR      NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    item_id      INT          REFERENCES item(item_id),
    strg_loc_id  INT          REFERENCES strg_location_stat(loc_id),
    ship_loc_id  INT          REFERENCES ship_location_stat(loc_id),
    req_at       TIMESTAMP    DEFAULT now(),
    start_at     TIMESTAMP,
    end_at       TIMESTAMP
);

CREATE TABLE equip_stat (
    stat_id     SERIAL       PRIMARY KEY,
    res_id      VARCHAR(10)  NOT NULL UNIQUE REFERENCES res(res_id),
    item_id     INT          REFERENCES item(item_id),
    txn_type    VARCHAR,
    cur_stat    VARCHAR      CHECK (cur_stat IN (
        'IDLE', 'ALLOC', 'FAIL',
        'MV_SRC', 'GRASP', 'MV_DEST', 'RELEASE', 'TO_IDLE',
        'ON', 'OFF'
    )),
    updated_at  TIMESTAMP    DEFAULT now(),
    err_msg     VARCHAR
);

-- =====================
-- TRANSPORT TASK / STATE
-- =====================

CREATE TABLE trans_task_txn (
    trans_task_txn_id  SERIAL       PRIMARY KEY,
    trans_id           VARCHAR(10)  REFERENCES trans(res_id),
    task_type          VARCHAR      NOT NULL CHECK (task_type IN ('ToPP', 'ToSTRG', 'ToSHIP', 'ToCHG')),
    txn_stat           VARCHAR      NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    chg_loc_id         INT          REFERENCES chg_location_stat(loc_id),
    item_id            INT          REFERENCES item(item_id),
    ord_id             INT          REFERENCES ord(ord_id),
    req_at             TIMESTAMP    DEFAULT now(),
    start_at           TIMESTAMP,
    end_at             TIMESTAMP
);

CREATE TABLE trans_stat (
    res_id        VARCHAR(10)  PRIMARY KEY REFERENCES trans(res_id),
    item_id       INT          REFERENCES item(item_id),
    cur_stat      VARCHAR      CHECK (cur_stat IN (
        'IDLE', 'ALLOC', 'CHG', 'TO_IDLE',
        'MV_SRC', 'WAIT_LD', 'MV_DEST', 'WAIT_DLD',
        'SUCC', 'FAIL'
    )),
    battery_pct   INT          CHECK (battery_pct >= 0 AND battery_pct <= 100),
    cur_zone_type INT,
    updated_at    TIMESTAMP    DEFAULT now()
);

-- =====================
-- INSPECTION
-- =====================

CREATE TABLE insp_task_txn (
    txn_id    SERIAL       PRIMARY KEY,
    item_id   INT          REFERENCES item(item_id),
    res_id    VARCHAR(10)  REFERENCES equip(res_id),
    txn_stat  VARCHAR(10)  NOT NULL CHECK (txn_stat IN ('QUE', 'PROC', 'SUCC', 'FAIL')),
    result    BOOLEAN,
    req_at    TIMESTAMP    DEFAULT now(),
    start_at  TIMESTAMP,
    end_at    TIMESTAMP
);

-- =====================
-- AI MODEL / INFERENCE
-- =====================

CREATE TABLE ai_model (
    model_id    SERIAL       PRIMARY KEY,
    model_nm    VARCHAR(50)  NOT NULL,
    model_type  VARCHAR(20)  NOT NULL CHECK (model_type IN ('YOLO', 'PATCHCORE')),
    target_cls  VARCHAR(5)   CHECK (target_cls IN ('CMH', 'RMH', 'EMH')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT now(),
    CONSTRAINT chk_patchcore_target_class CHECK (
        (model_type = 'YOLO'       AND target_cls IS NULL) OR
        (model_type = 'PATCHCORE'  AND target_cls IS NOT NULL)
    ),
    UNIQUE (model_nm, model_type, target_cls)
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
    item_id                 INT        REFERENCES item(item_id),
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
-- ERROR LOGS
-- =====================

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
    task_txn_id  INT          REFERENCES trans_task_txn(trans_task_txn_id),
    failed_stat  VARCHAR,
    err_msg      VARCHAR,
    battery_pct  INT,
    occured_at   TIMESTAMP    DEFAULT now()
);

-- =====================
-- ACTION / EVENT LOGS
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
    log_id            SERIAL     PRIMARY KEY,
    operator_id       INT        NOT NULL REFERENCES user_account(user_id),
    item_id           INT        REFERENCES item(item_id),
    pp_task_txn_id    INT        REFERENCES pp_task_txn(txn_id),
    button_device_id  VARCHAR,
    idempotency_key   VARCHAR    UNIQUE,
    ack_at            TIMESTAMP  DEFAULT now()
);

CREATE TABLE log_action_operator_rfid_scan (
    id               BIGSERIAL     NOT NULL,
    scanned_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    reader_id        VARCHAR       NOT NULL,
    zone             VARCHAR,
    raw_payload      VARCHAR       NOT NULL,
    ord_id           VARCHAR,
    item_key         VARCHAR,
    item_id          BIGINT,
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
    txn_id          INT           REFERENCES trans_task_txn(trans_task_txn_id),
    sensor_type     VARCHAR(30)   NOT NULL,
    raw_value       DECIMAL(10,4) NOT NULL,
    physical_value  DECIMAL(10,4),
    unit            VARCHAR(10),
    status          VARCHAR(10)   CHECK (status IN ('normal', 'warning', 'fault')),
    logged_at       TIMESTAMP     DEFAULT now()
);
