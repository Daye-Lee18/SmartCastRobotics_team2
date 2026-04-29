from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from smart_cast_db.database import Base


def _utc_now() -> datetime:
    return datetime.now(UTC)


# ────────────────────────────────────────
# 1. 주문 관리 (Order Management)
# ────────────────────────────────────────


class Order(Base):
    """주문 정보 — types.ts Order 대응"""

    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    customer_id = Column(String, nullable=False)
    customer_name = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    contact = Column(String, nullable=True, default="")
    # 고객 이메일 — /customer/lookup 의 이메일 기반 주문 조회에 사용 (2026-04-09 추가)
    email = Column(String, nullable=True, default="", index=True)
    shipping_address = Column(String, nullable=True, default="")
    total_amount = Column(Integer, nullable=False, default=0)
    # 주문 상태 (파이프라인):
    #   pending              접수 (고객 발주 직후)
    #   approved             승인 (관리자 승인)
    #   in_production        생산 (ProductionJob 생성 후)
    #   production_completed 생산 완료 (PyQt5 공정 시스템이 DB 에 기록)
    #   shipping_ready       출고 (관리자 '출고 처리' 클릭, shipped_at 자동 기록)
    #   completed            완료 (고객 수령)
    #   rejected             반려 (예외 분기)
    status = Column(String, nullable=False, default="pending")
    requested_delivery = Column(String, nullable=True)
    confirmed_delivery = Column(String, nullable=True, default="")
    created_at = Column(
        String,
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
    )
    updated_at = Column(
        String,
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
        onupdate=lambda: datetime.now(UTC).isoformat(),
    )
    # 출고 처리 시점 (shipping_ready 또는 completed 전환 시 자동 기록)
    shipped_at = Column(String, nullable=True, default="")


class OrderDetail(Base):
    """주문 상세 품목 — types.ts OrderDetail 대응"""

    __tablename__ = "order_details"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    spec = Column(String, nullable=True, default="")
    material = Column(String, nullable=True, default="")
    post_processing = Column(String, nullable=True, default="")
    logo_data = Column(String, nullable=True, default="")
    unit_price = Column(Integer, nullable=False, default=0)
    subtotal = Column(Integer, nullable=False, default=0)


class Product(Base):
    """제품 마스터 — src/app/customer/page.tsx PRODUCTS 와 1:1 매칭.

    프론트가 source of truth (2026-04-09): 하드코딩된 PRODUCTS 배열의 스키마를
    그대로 DB 로 옮긴 것. DB 조회 용도 위주이며, 프론트는 여전히 하드코딩을 사용한다.
    """

    __tablename__ = "products"

    # 도메인 ID (D450, D600, D800, GRATING)
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # 프론트 category (영문 키): "manhole" | "grating"
    category = Column(String, nullable=False)
    # 한글 라벨: "맨홀 뚜껑" | "그레이팅"
    category_label = Column(String, nullable=False, default="")
    # 요약 스펙 텍스트: "직경 450mm, KS 규격"
    spec = Column(String, nullable=False, default="")
    # 가격 범위 텍스트: "50,000 - 70,000원"
    price_range = Column(String, nullable=False, default="")
    base_price = Column(Integer, nullable=False, default=0)
    # 옵션 배열 (JSON 문자열로 저장, API 응답 시 list[str] 변환)
    diameter_options_json = Column(Text, nullable=False, default="[]")
    thickness_options_json = Column(Text, nullable=False, default="[]")
    materials_json = Column(Text, nullable=False, default="[]")
    load_class_range = Column(String, nullable=False, default="")
    # 부가 정보 (프론트에는 없으나 3D 뷰어 등에서 사용 예정)
    option_pricing_json = Column(Text, nullable=True, default="{}")
    design_image_url = Column(String, nullable=True, default="")
    model_3d_path = Column(String, nullable=True, default="")


class LoadClass(Base):
    """EN 124 하중 등급 마스터. products.load_class_range 의 코드 부분을 실제 톤수로 풀어줌."""

    __tablename__ = "load_classes"

    code = Column(String(8), primary_key=True)  # "A15", "B125", "C250", "D400", "E600", "F900"
    load_tons = Column(Float, nullable=False)  # 1.5, 12.5, 25.0, 40.0, 60.0, 90.0
    use_case = Column(String(200), nullable=False)  # "보행자 전용 구역" 등 설명
    display_order = Column(Integer, nullable=False)  # UI 정렬용 1~6


# ────────────────────────────────────────
# 2. 생산 모니터링 (Production Monitoring)
# ────────────────────────────────────────


class ProcessStage(Base):
    """공정 단계 상태 — types.ts ProcessStageData 대응"""

    __tablename__ = "process_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stage = Column(String, nullable=False)
    label = Column(String, nullable=False)
    status = Column(String, nullable=False, default="idle")
    temperature = Column(Float, nullable=True)
    target_temperature = Column(Float, nullable=True)
    progress = Column(Integer, nullable=False, default=0)
    start_time = Column(String, nullable=True)
    estimated_end = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    order_id = Column(String, nullable=True)
    job_id = Column(String, nullable=True)
    # 공정별 상세 데이터
    pressure = Column(Float, nullable=True)
    pour_angle = Column(Float, nullable=True)
    heating_power = Column(Float, nullable=True)
    cooling_progress = Column(Float, nullable=True)


# ────────────────────────────────────────
# 3. 통합 대시보드 (Equipment & Alerts)
# ────────────────────────────────────────


class Equipment(Base):
    """설비 정보 — types.ts Equipment 대응"""

    __tablename__ = "equipment"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    comm_id = Column(String, nullable=True, default="")
    install_location = Column(String, nullable=True, default="")
    status = Column(String, nullable=False, default="idle")
    pos_x = Column(Float, nullable=False, default=0.0)
    pos_y = Column(Float, nullable=False, default=0.0)
    pos_z = Column(Float, nullable=False, default=0.0)
    battery = Column(Integer, nullable=True)
    speed = Column(Float, nullable=True)
    last_update = Column(String, nullable=True)
    last_maintenance = Column(String, nullable=True)
    operating_hours = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)


class Alert(Base):
    """알림 — types.ts Alert 대응"""

    __tablename__ = "alerts"

    id = Column(String, primary_key=True, index=True)
    equipment_id = Column(String, nullable=True, default="")
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False, default="info")
    error_code = Column(String, nullable=True, default="")
    message = Column(String, nullable=False)
    abnormal_value = Column(String, nullable=True, default="")
    zone = Column(String, nullable=True)
    timestamp = Column(String, nullable=False)
    resolved_at = Column(String, nullable=True)
    acknowledged = Column(Boolean, nullable=False, default=False)


# ────────────────────────────────────────
# 4. 품질 검사 (Quality Control)
# ────────────────────────────────────────


class InspectionRecord(Base):
    """검사 기록 — types.ts InspectionRecord 대응"""

    __tablename__ = "inspection_records"

    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, nullable=True, default="")
    casting_id = Column(String, nullable=False)
    order_id = Column(String, nullable=True)
    result = Column(String, nullable=False)
    defect_type_code = Column(String, nullable=True, default="")
    confidence = Column(Float, nullable=False, default=0.0)
    inspector_id = Column(String, nullable=True, default="")
    image_id = Column(String, nullable=True)
    inspected_at = Column(String, nullable=False)
    defect_type = Column(String, nullable=True)
    defect_detail = Column(String, nullable=True)


class InspectionStandard(Base):
    """검사 기준 — types.ts InspectionStandard 대응"""

    __tablename__ = "inspection_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    tolerance_range = Column(String, nullable=False)
    target_dimension = Column(String, nullable=False)
    threshold = Column(Float, nullable=False, default=95.0)


class SorterLog(Base):
    """분류기 로그 — types.ts SorterLog 대응"""

    __tablename__ = "sorter_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inspection_id = Column(String, nullable=False)
    sort_direction = Column(String, nullable=False)
    sorter_angle = Column(Float, nullable=False, default=0.0)
    success = Column(Boolean, nullable=False, default=True)


# ────────────────────────────────────────
# 5. 물류 및 이송 (Logistics & Fleet)
# ────────────────────────────────────────


class TransportTask(Base):
    """이송 작업 — types.ts TransportTask 대응 (기존 TransportRequest 대체)"""

    __tablename__ = "transport_tasks"

    id = Column(String, primary_key=True, index=True)
    from_name = Column(String, nullable=False)
    from_coord = Column(String, nullable=True, default="")
    to_name = Column(String, nullable=False)
    to_coord = Column(String, nullable=True, default="")
    item_id = Column(String, nullable=True, default="")
    item_name = Column(String, nullable=True, default="")
    quantity = Column(Integer, nullable=False, default=1)
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="unassigned")
    assigned_robot_id = Column(String, nullable=True, default="")
    requested_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)


class HandoffAck(Base):
    """후처리존 인수인계 확인 이벤트 (SPEC-AMR-001).

    TimescaleDB hypertable. 버튼 이벤트 1건 = 1 row.
    @MX:ANCHOR: 핸드오프 감사 추적의 단일 진실 공급원. task_id=NULL 이면 orphan.
    @MX:REASON: Management Service 가 AMR FSM 전이와 함께 insert 하므로 누락 시 이력 손실.
    """

    __tablename__ = "handoff_acks"

    # DB 서버에 TimescaleDB 미설치 → 단순 PK 사용. 추후 hypertable 전환 시 (id, ack_at) 로 변경.
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ack_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    task_id = Column(
        String, ForeignKey("transport_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    zone = Column(String, nullable=False, index=True)
    amr_id = Column(String, nullable=True)
    ack_source = Column(
        String, nullable=False
    )  # 'esp32_button' | 'debug_endpoint' | 'gui_override'
    operator_id = Column(String, nullable=True)
    button_device_id = Column(String, nullable=True)
    orphan_ack = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String, nullable=True)
    extra = Column("metadata", JSONB, nullable=True)  # SQLAlchemy 의 metadata 충돌 회피


class WarehouseRack(Base):
    """창고 랙 — types.ts WarehouseRack 대응"""

    __tablename__ = "warehouse_racks"

    id = Column(String, primary_key=True, index=True)
    zone = Column(String, nullable=False)
    rack_number = Column(String, nullable=False)
    status = Column(String, nullable=False, default="empty")
    item_id = Column(String, nullable=True)
    item_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    last_inbound_at = Column(String, nullable=True)
    row = Column(Integer, nullable=False)
    col = Column(Integer, nullable=False)


class OutboundOrder(Base):
    """출고 주문 — types.ts OutboundOrder 대응"""

    __tablename__ = "outbound_orders"

    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    destination = Column(String, nullable=False)
    policy = Column(String, nullable=False, default="FIFO")
    completed = Column(Boolean, nullable=False, default=False)
    created_at = Column(String, nullable=False)


# ────────────────────────────────────────
# 차트/통계 (Charts / Statistics)
# ────────────────────────────────────────


class ProductionMetric(Base):
    """일별 생산 통계 — types.ts ProductionMetric 대응"""

    __tablename__ = "production_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False, index=True)
    production = Column(Integer, nullable=False, default=0)
    defects = Column(Integer, nullable=False, default=0)
    defect_rate = Column(Float, nullable=False, default=0.0)


# ────────────────────────────────────────
# 7. 생산 스케줄링 (Production Scheduling)
# ────────────────────────────────────────


class ProductionJob(Base):
    """생산 작업 — 주문을 공정에 할당한 작업 단위"""

    __tablename__ = "production_jobs"

    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    priority_score = Column(Float, nullable=False, default=0.0)
    priority_rank = Column(Integer, nullable=False, default=0)
    assigned_stage = Column(String, nullable=False, default="melting")
    status = Column(String, nullable=False, default="queued")  # queued/running/completed/cancelled
    estimated_completion = Column(String, nullable=True)
    started_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)
    created_at = Column(String, nullable=False)


class PriorityChangeLog(Base):
    """우선순위 변경 이력 — 수동 순서 변경 감사 추적"""

    __tablename__ = "priority_change_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, nullable=False, index=True)
    old_rank = Column(Integer, nullable=False)
    new_rank = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    changed_by = Column(String, nullable=False, default="admin")
    changed_at = Column(String, nullable=False)


# ============================================================================
# V6 아키텍처 (2026-04-14) — Confluence DB v47 공식 스키마 채택
# ============================================================================


class WorkOrder(Base):
    """생산 작업지시 — Confluence DB v47 의 work_order 테이블.

    승인된 발주(orders.status='approved')에 한해 생성. ProductionJob 를 대체.
    @MX:NOTE: status 값은 QUE/PROC/SUCC/FAIL (Confluence work_stat enum).
    """

    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)  # work_ord_id
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    pattern_id = Column(String, nullable=True)  # FK → order_detail.pattern_id (없으면 NULL)
    qty = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="QUE")  # QUE/PROC/SUCC/FAIL
    plan_start = Column(String, nullable=True)  # ISO 8601
    act_start = Column(String, nullable=True)
    act_end = Column(String, nullable=True)


class Item(Base):
    """개별 제품 1개 단위 실시간 공정 추적 — Confluence DB v47 의 Item 테이블.

    work_order.qty 만큼 생성. cur_stage 로 위치 추적, insp_id 로 검사 결과 연결.
    @MX:ANCHOR: V6 아키텍처의 핵심 추적 단위. UI 의 "주문별 제품 실시간 위치" 테이블이 직접 표시.
    @MX:REASON: 1개 생산되는 과정(생산+검사+적재)을 item_id 단위로 추적 (CASE1 채택).
    """

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, autoincrement=True)  # item_id
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False, index=True)
    cur_stage = Column(String(10), nullable=False, default="QUE")
    # cur_stage 값: QUE / MM / DM / TR_PP / PP / IP / TR_LD / SH
    curr_res = Column(String(10), nullable=True)  # 현재 점유 자원 (ARM1, AMR1 등)
    insp_id = Column(Integer, nullable=True)  # FK → inspection_records.id (검사 후)
    mfg_at = Column(String, nullable=True)  # 공정별 시작 시각 ISO 8601
