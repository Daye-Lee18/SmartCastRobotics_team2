"""Seed database with mock data matching frontend mock-data.ts."""

import json

from sqlalchemy.orm import Session

from app.models.models import (
    Alert,
    Equipment,
    InspectionRecord,
    InspectionStandard,
    LoadClass,
    Order,
    OrderDetail,
    OutboundOrder,
    PriorityChangeLog,  # noqa: F401 — 테이블 생성 보장
    ProcessStage,
    Product,
    ProductionJob,  # noqa: F401 — 테이블 생성 보장
    ProductionMetric,
    SorterLog,
    TransportTask,
    WarehouseRack,
)


def seed_database(db: Session) -> None:
    """모든 테이블에 mock 데이터 삽입 (중복 방지)."""
    _seed_orders(db)
    _seed_order_details(db)
    _seed_products(db)
    _seed_load_classes(db)
    _seed_process_stages(db)
    _seed_equipment(db)
    _seed_transport_tasks(db)
    _seed_warehouse_racks(db)
    _seed_outbound_orders(db)
    _seed_inspection_records(db)
    _seed_inspection_standards(db)
    _seed_sorter_logs(db)
    _seed_alerts(db)
    _seed_production_metrics(db)


# ────────────────────────────────────────
# 1. 주문 관리
# ────────────────────────────────────────


def _seed_orders(db: Session) -> None:
    if db.query(Order).count() > 0:
        return
    rows = [
        Order(
            id="ORD-2026-001",
            customer_id="CUST-001",
            customer_name="김철수",
            company_name="(주)한국도로공사",
            contact="02-1234-5678",
            shipping_address="서울특별시 성동구 용답동 123-4",
            total_amount=4250000,
            status="in_production",
            requested_delivery="2026-04-15",
            confirmed_delivery="2026-04-12",
            created_at="2026-03-25T09:00:00",
            updated_at="2026-03-28T14:30:00",
        ),
        Order(
            id="ORD-2026-002",
            customer_id="CUST-002",
            customer_name="이영희",
            company_name="(주)서울시설공단",
            contact="02-2345-6789",
            shipping_address="서울특별시 중구 세종대로 110",
            total_amount=3600000,
            status="approved",
            requested_delivery="2026-04-20",
            confirmed_delivery="2026-04-18",
            created_at="2026-03-26T10:00:00",
            updated_at="2026-03-27T11:00:00",
        ),
        Order(
            id="ORD-2026-003",
            customer_id="CUST-003",
            customer_name="박민수",
            company_name="(주)대한건설",
            contact="031-345-6789",
            shipping_address="경기도 수원시 장안구 정조로 123",
            total_amount=5500000,
            status="pending",
            requested_delivery="2026-05-01",
            confirmed_delivery="",
            created_at="2026-03-29T08:30:00",
            updated_at="2026-03-29T08:30:00",
        ),
        Order(
            id="ORD-2026-004",
            customer_id="CUST-004",
            customer_name="정수빈",
            company_name="(주)경기도시공사",
            contact="031-456-7890",
            shipping_address="경기도 성남시 분당구 정자동 45-6",
            total_amount=1700000,
            status="completed",
            requested_delivery="2026-03-28",
            confirmed_delivery="2026-03-27",
            created_at="2026-03-15T09:00:00",
            updated_at="2026-03-27T16:00:00",
        ),
        Order(
            id="ORD-2026-005",
            customer_id="CUST-005",
            customer_name="최동현",
            company_name="(주)부산항만공사",
            contact="051-567-8901",
            shipping_address="부산광역시 중구 충장대로 206",
            total_amount=7000000,
            status="pending",
            requested_delivery="2026-04-25",
            confirmed_delivery="",
            created_at="2026-03-30T07:00:00",
            updated_at="2026-03-30T07:00:00",
        ),
        Order(
            id="ORD-2026-006",
            customer_id="CUST-006",
            customer_name="한지민",
            company_name="(주)인천공항공사",
            contact="032-678-9012",
            shipping_address="인천광역시 중구 공항로 272",
            total_amount=9200000,
            status="approved",
            requested_delivery="2026-04-10",
            confirmed_delivery="",
            created_at="2026-03-24T11:00:00",
            updated_at="2026-03-28T09:00:00",
        ),
        Order(
            id="ORD-2026-007",
            customer_id="CUST-007",
            customer_name="윤서준",
            company_name="(주)대전도시공사",
            contact="042-789-0123",
            shipping_address="대전광역시 서구 둔산로 100",
            total_amount=2400000,
            status="approved",
            requested_delivery="2026-04-30",
            confirmed_delivery="",
            created_at="2026-03-31T08:00:00",
            updated_at="2026-04-01T10:00:00",
        ),
        Order(
            id="ORD-2026-008",
            customer_id="CUST-008",
            customer_name="강예린",
            company_name="(주)울산항만공사",
            contact="052-890-1234",
            shipping_address="울산광역시 남구 장생포로 55",
            total_amount=4800000,
            status="approved",
            requested_delivery="2026-04-08",
            confirmed_delivery="",
            created_at="2026-03-22T07:30:00",
            updated_at="2026-03-25T14:00:00",
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_order_details(db: Session) -> None:
    if db.query(OrderDetail).count() > 0:
        return
    rows = [
        OrderDetail(
            id="OD-001",
            order_id="ORD-2026-001",
            product_id="PRD-001",
            product_name="맨홀 뚜껑 KS D-600",
            quantity=50,
            spec="600mm / 두께 50mm / EN124 D400",
            material="GCD450 (구상흑연주철)",
            post_processing="표면 연마 + 방청 코팅",
            logo_data="한국도로공사 로고",
            unit_price=85000,
            subtotal=4250000,
        ),
        OrderDetail(
            id="OD-002",
            order_id="ORD-2026-002",
            product_id="PRD-002",
            product_name="맨홀 뚜껑 KS D-800",
            quantity=30,
            spec="800mm / 두께 60mm / EN124 E600",
            material="GCD500 (구상흑연주철)",
            post_processing="표면 연마",
            logo_data="",
            unit_price=120000,
            subtotal=3600000,
        ),
        OrderDetail(
            id="OD-003",
            order_id="ORD-2026-003",
            product_id="PRD-003",
            product_name="맨홀 뚜껑 KS D-450",
            quantity=100,
            spec="450mm / 두께 40mm / EN124 C250",
            material="FC250 (회주철)",
            post_processing="방청 코팅",
            logo_data="",
            unit_price=55000,
            subtotal=5500000,
        ),
        OrderDetail(
            id="OD-004",
            order_id="ORD-2026-004",
            product_id="PRD-001",
            product_name="맨홀 뚜껑 KS D-600",
            quantity=20,
            spec="600mm / 두께 50mm / EN124 D400",
            material="GCD450 (구상흑연주철)",
            post_processing="표면 연마 + 방청 코팅 + 문구 삽입",
            logo_data="경기도시공사 문구",
            unit_price=85000,
            subtotal=1700000,
        ),
        OrderDetail(
            id="OD-005",
            order_id="ORD-2026-005",
            product_id="PRD-005",
            product_name="배수구 그레이팅",
            quantity=200,
            spec="500x300mm / 두께 30mm",
            material="FC200 (회주철)",
            post_processing="아연 도금",
            logo_data="",
            unit_price=35000,
            subtotal=7000000,
        ),
        OrderDetail(
            id="OD-006",
            order_id="ORD-2026-006",
            product_id="PRD-002",
            product_name="맨홀 뚜껑 KS D-800",
            quantity=80,
            spec="800mm / 두께 60mm / EN124 E600",
            material="GCD500 (구상흑연주철)",
            post_processing="표면 연마 + 방청 코팅",
            logo_data="인천공항공사 로고",
            unit_price=115000,
            subtotal=9200000,
        ),
        OrderDetail(
            id="OD-007",
            order_id="ORD-2026-007",
            product_id="PRD-003",
            product_name="맨홀 뚜껑 KS D-450",
            quantity=40,
            spec="450mm / 두께 40mm / EN124 C250",
            material="FC250 (회주철)",
            post_processing="방청 코팅",
            logo_data="",
            unit_price=60000,
            subtotal=2400000,
        ),
        OrderDetail(
            id="OD-008",
            order_id="ORD-2026-008",
            product_id="PRD-001",
            product_name="맨홀 뚜껑 KS D-600",
            quantity=60,
            spec="600mm / 두께 50mm / EN124 D400",
            material="GCD450 (구상흑연주철)",
            post_processing="아연 도금 + 내염수 코팅",
            logo_data="울산항만공사 문구",
            unit_price=80000,
            subtotal=4800000,
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_products(db: Session) -> None:
    """프론트 src/app/customer/page.tsx PRODUCTS 배열과 동기화된 4개 제품."""
    if db.query(Product).count() > 0:
        return

    def _dump(value) -> str:
        return json.dumps(value, ensure_ascii=False)

    rows = [
        Product(
            id="D450",
            name="맨홀 뚜껑 KS D-450",
            category="manhole",
            category_label="맨홀 뚜껑",
            spec="직경 450mm, KS 규격",
            price_range="50,000 - 70,000원",
            base_price=55000,
            diameter_options_json=_dump(["450mm", "460mm", "470mm"]),
            thickness_options_json=_dump(["25mm", "30mm", "35mm", "40mm"]),
            materials_json=_dump(["FC200", "FC250", "GCD450"]),
            load_class_range="B125 ~ D400",
            option_pricing_json=_dump({"표면 연마": 3000, "방청 코팅": 2000}),
            design_image_url="/images/products/manhole-450.png",
            model_3d_path="/models/manhole-450.glb",
        ),
        Product(
            id="D600",
            name="맨홀 뚜껑 KS D-600",
            category="manhole",
            category_label="맨홀 뚜껑",
            spec="직경 600mm, KS 규격",
            price_range="75,000 - 100,000원",
            base_price=85000,
            diameter_options_json=_dump(["600mm", "610mm", "620mm"]),
            thickness_options_json=_dump(["30mm", "35mm", "40mm", "45mm"]),
            materials_json=_dump(["FC200", "FC250", "GCD450", "GCD500"]),
            load_class_range="B125 ~ F900",
            option_pricing_json=_dump({"표면 연마": 5000, "방청 코팅": 3000, "로고 삽입": 8000}),
            design_image_url="/images/products/manhole-600.png",
            model_3d_path="/models/manhole-600.glb",
        ),
        Product(
            id="D800",
            name="맨홀 뚜껑 KS D-800",
            category="manhole",
            category_label="맨홀 뚜껑",
            spec="직경 800mm, KS 규격",
            price_range="110,000 - 140,000원",
            base_price=120000,
            diameter_options_json=_dump(["800mm", "810mm", "820mm"]),
            thickness_options_json=_dump(["35mm", "40mm", "45mm", "50mm"]),
            materials_json=_dump(["FC250", "GCD450", "GCD500"]),
            load_class_range="C250 ~ F900",
            option_pricing_json=_dump({"표면 연마": 7000, "방청 코팅": 4000, "로고 삽입": 10000}),
            design_image_url="/images/products/manhole-800.png",
            model_3d_path="/models/manhole-800.glb",
        ),
        Product(
            id="GRATING",
            name="배수구 그레이팅 500x300",
            category="grating",
            category_label="그레이팅",
            spec="500x300mm, 격자형",
            price_range="30,000 - 45,000원",
            base_price=35000,
            diameter_options_json=_dump(["500x300mm", "500x350mm", "600x300mm"]),
            thickness_options_json=_dump(["20mm", "25mm", "30mm"]),
            materials_json=_dump(["FC200", "FC250"]),
            load_class_range="B125 ~ C250",
            option_pricing_json=_dump({"아연 도금": 5000, "내식 코팅": 7000}),
            design_image_url="/images/products/grating-500.png",
            model_3d_path="/models/grating-500.glb",
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_load_classes(db: Session) -> None:
    """EN 124 하중 등급 마스터 6개."""
    if db.query(LoadClass).count() > 0:
        return
    rows = [
        LoadClass(code="A15", load_tons=1.5, use_case="보행자 전용 구역", display_order=1),
        LoadClass(
            code="B125", load_tons=12.5, use_case="자전거·보행자 도로, 주차장", display_order=2
        ),
        LoadClass(
            code="C250", load_tons=25.0, use_case="길가·갓길 (상용차 주차 가능)", display_order=3
        ),
        LoadClass(code="D400", load_tons=40.0, use_case="일반 차도", display_order=4),
        LoadClass(code="E600", load_tons=60.0, use_case="항만·산업 구역", display_order=5),
        LoadClass(code="F900", load_tons=90.0, use_case="공항·특수 중하중 지역", display_order=6),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 2. 생산 모니터링
# ────────────────────────────────────────


def _seed_process_stages(db: Session) -> None:
    if db.query(ProcessStage).count() > 0:
        return
    rows = [
        ProcessStage(
            stage="melting",
            label="용해",
            status="running",
            temperature=1420.0,
            target_temperature=1450.0,
            progress=85,
            start_time="2026-03-30T08:00:00",
            estimated_end="2026-03-30T09:30:00",
            equipment_id="FRN-001",
            order_id="ORD-2026-001",
            job_id="JOB-0301",
            heating_power=92.0,
        ),
        ProcessStage(
            stage="molding",
            label="주형 제작",
            status="completed",
            progress=100,
            start_time="2026-03-30T07:00:00",
            estimated_end="2026-03-30T08:00:00",
            equipment_id="MLD-001",
            order_id="ORD-2026-001",
            job_id="JOB-0301",
            pressure=85.0,
        ),
        ProcessStage(
            stage="pouring",
            label="주탕",
            status="waiting",
            temperature=1400.0,
            target_temperature=1400.0,
            progress=0,
            equipment_id="ARM-001",
            order_id="ORD-2026-001",
            job_id="JOB-0301",
            pour_angle=45.0,
        ),
        ProcessStage(
            stage="cooling",
            label="냉각",
            status="running",
            temperature=320.0,
            target_temperature=25.0,
            progress=60,
            start_time="2026-03-30T06:00:00",
            estimated_end="2026-03-30T10:00:00",
            equipment_id="CLZ-001",
            order_id="ORD-2026-001",
            job_id="JOB-0300",
            cooling_progress=60.0,
        ),
        ProcessStage(
            stage="demolding",
            label="탈형",
            status="idle",
            progress=0,
            equipment_id="ARM-002",
            order_id="ORD-2026-001",
            job_id="JOB-0300",
        ),
        ProcessStage(
            stage="post_processing",
            label="후처리",
            status="running",
            progress=45,
            start_time="2026-03-30T09:00:00",
            estimated_end="2026-03-30T10:30:00",
            equipment_id="ARM-003",
            order_id="ORD-2026-001",
            job_id="JOB-0299",
        ),
        ProcessStage(
            stage="inspection",
            label="검사",
            status="running",
            progress=70,
            start_time="2026-03-30T09:30:00",
            estimated_end="2026-03-30T10:00:00",
            equipment_id="CAM-001",
            order_id="ORD-2026-001",
            job_id="JOB-0298",
        ),
        ProcessStage(
            stage="classification",
            label="분류",
            status="idle",
            progress=0,
            equipment_id="SRT-001",
            order_id="ORD-2026-001",
            job_id="JOB-0298",
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 3. 설비 관리
# ────────────────────────────────────────


def _seed_equipment(db: Session) -> None:
    if db.query(Equipment).count() > 0:
        return
    rows = [
        Equipment(
            id="FRN-001",
            name="용해로 #1",
            type="furnace",
            comm_id="192.168.1.101",
            install_location="용해 구역 A동",
            status="running",
            pos_x=2.0,
            pos_y=1.0,
            pos_z=0.0,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-20",
            operating_hours=1250,
            error_count=0,
        ),
        Equipment(
            id="FRN-002",
            name="용해로 #2",
            type="furnace",
            comm_id="192.168.1.102",
            install_location="용해 구역 A동",
            status="idle",
            pos_x=4.0,
            pos_y=1.0,
            pos_z=0.0,
            last_update="2026-03-30T09:45:00",
            last_maintenance="2026-03-18",
            operating_hours=980,
            error_count=1,
        ),
        Equipment(
            id="MLD-001",
            name="조형기 #1",
            type="mold_press",
            comm_id="192.168.1.110",
            install_location="주형 구역 B동",
            status="running",
            pos_x=8.0,
            pos_y=1.0,
            pos_z=0.0,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-22",
            operating_hours=890,
            error_count=0,
        ),
        Equipment(
            id="ARM-001",
            name="로봇암 #1 (주탕)",
            type="robot_arm",
            comm_id="192.168.1.120",
            install_location="주조 구역 C동",
            status="idle",
            pos_x=12.0,
            pos_y=2.0,
            pos_z=0.0,
            last_update="2026-03-30T09:50:00",
            last_maintenance="2026-03-25",
            operating_hours=650,
            error_count=0,
        ),
        Equipment(
            id="ARM-002",
            name="로봇암 #2 (탈형)",
            type="robot_arm",
            comm_id="192.168.1.121",
            install_location="냉각 구역 D동",
            status="idle",
            pos_x=16.0,
            pos_y=2.0,
            pos_z=0.0,
            last_update="2026-03-30T09:48:00",
            last_maintenance="2026-03-24",
            operating_hours=720,
            error_count=2,
        ),
        Equipment(
            id="ARM-003",
            name="로봇암 #3 (후처리)",
            type="robot_arm",
            comm_id="192.168.1.122",
            install_location="후처리 구역 E동",
            status="running",
            pos_x=20.0,
            pos_y=2.0,
            pos_z=0.0,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-26",
            operating_hours=540,
            error_count=0,
        ),
        Equipment(
            id="AMR-001",
            name="AMR #1",
            type="amr",
            comm_id="ros2://amr_01/cmd_vel",
            install_location="이송 구역",
            status="running",
            pos_x=14.0,
            pos_y=5.0,
            pos_z=0.0,
            battery=78,
            speed=1.2,
            last_update="2026-03-30T10:01:00",
            last_maintenance="2026-03-28",
            operating_hours=320,
            error_count=0,
        ),
        Equipment(
            id="AMR-002",
            name="AMR #2",
            type="amr",
            comm_id="ros2://amr_02/cmd_vel",
            install_location="대기 장소",
            status="idle",
            pos_x=6.0,
            pos_y=8.0,
            pos_z=0.0,
            battery=95,
            speed=0.0,
            last_update="2026-03-30T09:55:00",
            last_maintenance="2026-03-27",
            operating_hours=280,
            error_count=0,
        ),
        Equipment(
            id="AMR-003",
            name="AMR #3",
            type="amr",
            comm_id="ros2://amr_03/cmd_vel",
            install_location="충전소",
            status="charging",
            pos_x=1.0,
            pos_y=8.0,
            pos_z=0.0,
            battery=12,
            speed=0.0,
            last_update="2026-03-30T09:40:00",
            last_maintenance="2026-03-29",
            operating_hours=410,
            error_count=1,
        ),
        Equipment(
            id="CVR-001",
            name="컨베이어 #1",
            type="conveyor",
            comm_id="192.168.1.130",
            install_location="검사 구역 F동",
            status="running",
            pos_x=24.0,
            pos_y=3.0,
            pos_z=0.0,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-21",
            operating_hours=1100,
            error_count=0,
        ),
        Equipment(
            id="CAM-001",
            name="검사 카메라 #1",
            type="camera",
            comm_id="192.168.1.140",
            install_location="검사 구역 F동",
            status="running",
            pos_x=25.0,
            pos_y=3.0,
            pos_z=1.5,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-23",
            operating_hours=800,
            error_count=0,
        ),
        Equipment(
            id="SRT-001",
            name="분류기 #1",
            type="sorter",
            comm_id="192.168.1.150",
            install_location="분류 구역 F동",
            status="running",
            pos_x=28.0,
            pos_y=3.0,
            pos_z=0.0,
            last_update="2026-03-30T10:00:00",
            last_maintenance="2026-03-19",
            operating_hours=950,
            error_count=0,
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 4. 이송 / 물류
# ────────────────────────────────────────


def _seed_transport_tasks(db: Session) -> None:
    if db.query(TransportTask).count() > 0:
        return
    rows = [
        TransportTask(
            id="TRN-001",
            from_name="주조 구역 C동",
            from_coord="12,2",
            to_name="후처리 구역 E동",
            to_coord="20,2",
            item_id="CST-0301-B1",
            item_name="주물 팔레트",
            quantity=5,
            priority="high",
            status="moving_to_dest",
            assigned_robot_id="AMR-001",
            requested_at="2026-03-30T09:15:00",
        ),
        TransportTask(
            id="TRN-002",
            from_name="후처리 구역 E동",
            from_coord="20,2",
            to_name="검사 구역 F동",
            to_coord="24,3",
            item_id="CST-0300-PP",
            item_name="후처리 완료 주물",
            quantity=3,
            priority="medium",
            status="unassigned",
            assigned_robot_id="",
            requested_at="2026-03-30T09:30:00",
        ),
        TransportTask(
            id="TRN-003",
            from_name="검사 구역 F동",
            from_coord="24,3",
            to_name="적재 구역 G동",
            to_coord="30,5",
            item_id="CST-0298-OK",
            item_name="양품 팔레트",
            quantity=10,
            priority="medium",
            status="completed",
            assigned_robot_id="AMR-002",
            requested_at="2026-03-30T08:00:00",
            completed_at="2026-03-30T08:25:00",
        ),
        TransportTask(
            id="TRN-004",
            from_name="검사 구역 F동",
            from_coord="24,3",
            to_name="폐기물 구역 H동",
            to_coord="32,8",
            item_id="CST-0298-NG",
            item_name="불량품 박스",
            quantity=2,
            priority="low",
            status="completed",
            assigned_robot_id="AMR-001",
            requested_at="2026-03-30T08:30:00",
            completed_at="2026-03-30T08:45:00",
        ),
        TransportTask(
            id="TRN-005",
            from_name="적재 구역 G동",
            from_coord="30,5",
            to_name="출하 구역 I동",
            to_coord="34,1",
            item_id="CST-0295-SHP",
            item_name="출고 팔레트",
            quantity=8,
            priority="high",
            status="assigned",
            assigned_robot_id="AMR-002",
            requested_at="2026-03-30T09:45:00",
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 5. 창고 랙
# ────────────────────────────────────────


def _seed_warehouse_racks(db: Session) -> None:
    if db.query(WarehouseRack).count() > 0:
        return

    rack_statuses = [
        "occupied",
        "empty",
        "occupied",
        "reserved",
        "empty",
        "occupied",
        "occupied",
        "empty",
        "unavailable",
        "occupied",
        "empty",
        "occupied",
        "occupied",
        "occupied",
        "empty",
        "empty",
        "occupied",
        "reserved",
        "empty",
        "occupied",
        "empty",
        "empty",
        "occupied",
        "occupied",
    ]
    rack_items = [
        ("PRD-001", "맨홀 뚜껑 KS D-600", 8),
        ("PRD-002", "맨홀 뚜껑 KS D-800", 4),
        ("PRD-003", "맨홀 뚜껑 KS D-450", 12),
        ("PRD-004", "빗물받이 KS D-300", 6),
        ("PRD-005", "배수구 그레이팅", 15),
        ("PRD-001", "맨홀 뚜껑 KS D-600", 5),
        ("PRD-002", "맨홀 뚜껑 KS D-800", 3),
        ("PRD-003", "맨홀 뚜껑 KS D-450", 10),
        ("PRD-005", "배수구 그레이팅", 7),
        ("PRD-001", "맨홀 뚜껑 KS D-600", 9),
        ("PRD-004", "빗물받이 KS D-300", 4),
        ("PRD-003", "맨홀 뚜껑 KS D-450", 6),
        ("PRD-005", "배수구 그레이팅", 11),
        ("PRD-002", "맨홀 뚜껑 KS D-800", 2),
    ]

    rows = []
    for i in range(24):
        row = (i // 6) + 1
        col = (i % 6) + 1
        status = rack_statuses[i]
        rack_id = f"RCK-{row:02d}-{col:02d}"
        zone = "A구역" if row <= 2 else "B구역"
        rack_number = f"{row:02d}-{col:02d}"

        rack = WarehouseRack(
            id=rack_id,
            zone=zone,
            rack_number=rack_number,
            status=status,
            row=row,
            col=col,
        )
        if status in ("occupied", "reserved"):
            item_idx = i % len(rack_items)
            item_id, item_name, qty = rack_items[item_idx]
            rack.item_id = item_id
            rack.item_name = item_name
            rack.quantity = qty
            rack.last_inbound_at = "2026-03-30T09:00:00"

        rows.append(rack)

    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 6. 출고 주문
# ────────────────────────────────────────


def _seed_outbound_orders(db: Session) -> None:
    if db.query(OutboundOrder).count() > 0:
        return
    rows = [
        OutboundOrder(
            id="OUT-001",
            product_id="PRD-001",
            product_name="맨홀 뚜껑 KS D-600",
            quantity=20,
            destination="(주)경기도시공사",
            policy="FIFO",
            completed=True,
            created_at="2026-03-27T10:00:00",
        ),
        OutboundOrder(
            id="OUT-002",
            product_id="PRD-002",
            product_name="맨홀 뚜껑 KS D-800",
            quantity=10,
            destination="(주)서울시설공단",
            policy="FIFO",
            completed=False,
            created_at="2026-03-30T08:00:00",
        ),
        OutboundOrder(
            id="OUT-003",
            product_id="PRD-005",
            product_name="배수구 그레이팅",
            quantity=50,
            destination="(주)부산항만공사",
            policy="LIFO",
            completed=False,
            created_at="2026-03-30T09:00:00",
        ),
        OutboundOrder(
            id="OUT-004",
            product_id="PRD-003",
            product_name="맨홀 뚜껑 KS D-450",
            quantity=30,
            destination="(주)대한건설",
            policy="FIFO",
            completed=False,
            created_at="2026-03-30T11:00:00",
        ),
        OutboundOrder(
            id="OUT-005",
            product_id="PRD-004",
            product_name="빗물받이 KS D-300",
            quantity=15,
            destination="(주)인천항만공사",
            policy="FIFO",
            completed=True,
            created_at="2026-03-28T14:00:00",
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 7. 품질 검사
# ────────────────────────────────────────


def _seed_inspection_records(db: Session) -> None:
    if db.query(InspectionRecord).count() > 0:
        return
    rows = [
        # ORD-2026-004 검사 기록
        InspectionRecord(
            id="INS-001",
            product_id="PRD-001",
            casting_id="CST-0298-01",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=98.5,
            inspector_id="CAM-001",
            image_id="IMG-001",
            inspected_at="2026-03-30T09:31:00",
        ),
        InspectionRecord(
            id="INS-002",
            product_id="PRD-001",
            casting_id="CST-0298-02",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=97.2,
            inspector_id="CAM-001",
            image_id="IMG-002",
            inspected_at="2026-03-30T09:32:00",
        ),
        InspectionRecord(
            id="INS-003",
            product_id="PRD-001",
            casting_id="CST-0298-03",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D01",
            confidence=95.8,
            inspector_id="CAM-001",
            image_id="IMG-003",
            inspected_at="2026-03-30T09:33:00",
            defect_type="표면 균열",
            defect_detail="뚜껑 외곽부 0.3mm 크랙",
        ),
        InspectionRecord(
            id="INS-004",
            product_id="PRD-001",
            casting_id="CST-0298-04",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=99.1,
            inspector_id="CAM-001",
            image_id="IMG-004",
            inspected_at="2026-03-30T09:34:00",
        ),
        InspectionRecord(
            id="INS-005",
            product_id="PRD-001",
            casting_id="CST-0298-05",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=96.7,
            inspector_id="CAM-001",
            image_id="IMG-005",
            inspected_at="2026-03-30T09:35:00",
        ),
        InspectionRecord(
            id="INS-006",
            product_id="PRD-001",
            casting_id="CST-0298-06",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D02",
            confidence=94.3,
            inspector_id="CAM-001",
            image_id="IMG-006",
            inspected_at="2026-03-30T09:36:00",
            defect_type="기포 불량",
            defect_detail="내부 기포 2개 감지 (직경 1.5mm)",
        ),
        InspectionRecord(
            id="INS-007",
            product_id="PRD-001",
            casting_id="CST-0298-07",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=98.0,
            inspector_id="CAM-001",
            image_id="IMG-007",
            inspected_at="2026-03-30T09:37:00",
        ),
        InspectionRecord(
            id="INS-008",
            product_id="PRD-001",
            casting_id="CST-0298-08",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=97.5,
            inspector_id="CAM-001",
            image_id="IMG-008",
            inspected_at="2026-03-30T09:38:00",
        ),
        # ORD-2026-001 검사 기록 (생산 중)
        InspectionRecord(
            id="INS-009",
            product_id="PRD-001",
            casting_id="CST-0301-01",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=98.8,
            inspector_id="CAM-001",
            image_id="IMG-009",
            inspected_at="2026-03-30T10:01:00",
        ),
        InspectionRecord(
            id="INS-010",
            product_id="PRD-001",
            casting_id="CST-0301-02",
            order_id="ORD-2026-001",
            result="fail",
            defect_type_code="D03",
            confidence=92.1,
            inspector_id="CAM-001",
            image_id="IMG-010",
            inspected_at="2026-03-30T10:02:30",
            defect_type="수축 결함",
            defect_detail="중앙부 수축 3mm 초과",
        ),
        InspectionRecord(
            id="INS-011",
            product_id="PRD-001",
            casting_id="CST-0301-03",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=97.9,
            inspector_id="CAM-001",
            image_id="IMG-011",
            inspected_at="2026-03-30T10:04:00",
        ),
        InspectionRecord(
            id="INS-012",
            product_id="PRD-001",
            casting_id="CST-0301-04",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=99.3,
            inspector_id="CAM-001",
            image_id="IMG-012",
            inspected_at="2026-03-30T10:05:30",
        ),
        InspectionRecord(
            id="INS-013",
            product_id="PRD-001",
            casting_id="CST-0301-05",
            order_id="ORD-2026-001",
            result="fail",
            defect_type_code="D01",
            confidence=96.4,
            inspector_id="CAM-001",
            image_id="IMG-013",
            inspected_at="2026-03-30T10:07:00",
            defect_type="표면 균열",
            defect_detail="테두리 미세 균열 0.2mm",
        ),
        InspectionRecord(
            id="INS-014",
            product_id="PRD-001",
            casting_id="CST-0301-06",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=98.2,
            inspector_id="CAM-001",
            image_id="IMG-014",
            inspected_at="2026-03-30T10:08:30",
        ),
        InspectionRecord(
            id="INS-015",
            product_id="PRD-001",
            casting_id="CST-0301-07",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=97.0,
            inspector_id="CAM-001",
            image_id="IMG-015",
            inspected_at="2026-03-30T10:10:00",
        ),
        InspectionRecord(
            id="INS-016",
            product_id="PRD-001",
            casting_id="CST-0301-08",
            order_id="ORD-2026-001",
            result="fail",
            defect_type_code="D06",
            confidence=93.7,
            inspector_id="CAM-001",
            image_id="IMG-016",
            inspected_at="2026-03-30T10:11:30",
            defect_type="주탕 불량",
            defect_detail="미충전 부위 발생",
        ),
        InspectionRecord(
            id="INS-017",
            product_id="PRD-001",
            casting_id="CST-0301-09",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=98.6,
            inspector_id="CAM-001",
            image_id="IMG-017",
            inspected_at="2026-03-30T10:13:00",
        ),
        InspectionRecord(
            id="INS-018",
            product_id="PRD-001",
            casting_id="CST-0301-10",
            order_id="ORD-2026-001",
            result="pass",
            defect_type_code="",
            confidence=99.0,
            inspector_id="CAM-001",
            image_id="IMG-018",
            inspected_at="2026-03-30T10:14:30",
        ),
        # 이전 주문 검사 기록
        InspectionRecord(
            id="INS-019",
            product_id="PRD-001",
            casting_id="CST-0295-01",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D04",
            confidence=91.5,
            inspector_id="CAM-001",
            image_id="IMG-019",
            inspected_at="2026-03-29T14:20:00",
            defect_type="치수 불량",
            defect_detail="외경 601.5mm (허용 +-0.5mm)",
        ),
        InspectionRecord(
            id="INS-020",
            product_id="PRD-001",
            casting_id="CST-0295-02",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=98.3,
            inspector_id="CAM-001",
            image_id="IMG-020",
            inspected_at="2026-03-29T14:21:30",
        ),
        InspectionRecord(
            id="INS-021",
            product_id="PRD-001",
            casting_id="CST-0295-03",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D02",
            confidence=89.8,
            inspector_id="CAM-001",
            image_id="IMG-021",
            inspected_at="2026-03-29T14:23:00",
            defect_type="기포 불량",
            defect_detail="표면 기포 다수 (5개 이상)",
        ),
        InspectionRecord(
            id="INS-022",
            product_id="PRD-001",
            casting_id="CST-0295-04",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=97.6,
            inspector_id="CAM-001",
            image_id="IMG-022",
            inspected_at="2026-03-29T14:24:30",
        ),
        InspectionRecord(
            id="INS-023",
            product_id="PRD-001",
            casting_id="CST-0295-05",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D05",
            confidence=93.2,
            inspector_id="CAM-001",
            image_id="IMG-023",
            inspected_at="2026-03-29T14:26:00",
            defect_type="냉각 균열",
            defect_detail="급속 냉각 열응력 균열",
        ),
        InspectionRecord(
            id="INS-024",
            product_id="PRD-001",
            casting_id="CST-0295-06",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=99.4,
            inspector_id="CAM-001",
            image_id="IMG-024",
            inspected_at="2026-03-29T14:27:30",
        ),
        InspectionRecord(
            id="INS-025",
            product_id="PRD-001",
            casting_id="CST-0295-07",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D07",
            confidence=90.1,
            inspector_id="CAM-001",
            image_id="IMG-025",
            inspected_at="2026-03-29T14:29:00",
            defect_type="주형 결함",
            defect_detail="주형 파손에 의한 형상 이상",
        ),
        InspectionRecord(
            id="INS-026",
            product_id="PRD-001",
            casting_id="CST-0295-08",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=96.9,
            inspector_id="CAM-001",
            image_id="IMG-026",
            inspected_at="2026-03-29T14:30:30",
        ),
        InspectionRecord(
            id="INS-027",
            product_id="PRD-001",
            casting_id="CST-0295-09",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D01",
            confidence=88.7,
            inspector_id="CAM-001",
            image_id="IMG-027",
            inspected_at="2026-03-29T14:32:00",
            defect_type="표면 균열",
            defect_detail="하부면 균열 0.5mm",
        ),
        InspectionRecord(
            id="INS-028",
            product_id="PRD-001",
            casting_id="CST-0295-10",
            order_id="ORD-2026-004",
            result="pass",
            defect_type_code="",
            confidence=98.1,
            inspector_id="CAM-001",
            image_id="IMG-028",
            inspected_at="2026-03-29T14:33:30",
        ),
        InspectionRecord(
            id="INS-029",
            product_id="PRD-001",
            casting_id="CST-0296-01",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D03",
            confidence=91.9,
            inspector_id="CAM-001",
            image_id="IMG-029",
            inspected_at="2026-03-29T15:10:00",
            defect_type="수축 결함",
            defect_detail="냉각 수축률 기준 초과",
        ),
        InspectionRecord(
            id="INS-030",
            product_id="PRD-001",
            casting_id="CST-0296-02",
            order_id="ORD-2026-004",
            result="fail",
            defect_type_code="D02",
            confidence=87.3,
            inspector_id="CAM-001",
            image_id="IMG-030",
            inspected_at="2026-03-29T15:11:30",
            defect_type="기포 불량",
            defect_detail="내부 기포 밀집 구간",
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_inspection_standards(db: Session) -> None:
    if db.query(InspectionStandard).count() > 0:
        return
    rows = [
        InspectionStandard(
            product_id="PRD-001",
            product_name="맨홀 뚜껑 KS D-600",
            tolerance_range="+-0.5mm",
            target_dimension="외경 600mm / 두께 50mm",
            threshold=95.0,
        ),
        InspectionStandard(
            product_id="PRD-002",
            product_name="맨홀 뚜껑 KS D-800",
            tolerance_range="+-0.8mm",
            target_dimension="외경 800mm / 두께 60mm",
            threshold=95.0,
        ),
        InspectionStandard(
            product_id="PRD-003",
            product_name="맨홀 뚜껑 KS D-450",
            tolerance_range="+-0.4mm",
            target_dimension="외경 450mm / 두께 40mm",
            threshold=93.0,
        ),
    ]
    db.add_all(rows)
    db.commit()


def _seed_sorter_logs(db: Session) -> None:
    if db.query(SorterLog).count() > 0:
        return
    rows = [
        SorterLog(
            inspection_id="INS-001", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-002", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-003", sort_direction="fail_line", sorter_angle=45.0, success=True
        ),
        SorterLog(
            inspection_id="INS-004", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-005", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-006", sort_direction="fail_line", sorter_angle=45.0, success=True
        ),
        SorterLog(
            inspection_id="INS-007", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-008", sort_direction="pass_line", sorter_angle=0.0, success=False
        ),
        SorterLog(
            inspection_id="INS-009", sort_direction="pass_line", sorter_angle=0.0, success=True
        ),
        SorterLog(
            inspection_id="INS-010", sort_direction="fail_line", sorter_angle=45.0, success=True
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 8. 알림
# ────────────────────────────────────────


def _seed_alerts(db: Session) -> None:
    if db.query(Alert).count() > 0:
        return
    rows = [
        Alert(
            id="ALT-001",
            equipment_id="AMR-003",
            type="equipment_error",
            severity="critical",
            error_code="E-AMR-BAT-LOW",
            message="AMR #3 배터리 부족 - 충전 필요 (12%)",
            abnormal_value="배터리 12% (임계값 15%)",
            zone="이송 구역",
            timestamp="2026-03-30T09:40:00",
            acknowledged=False,
        ),
        Alert(
            id="ALT-002",
            equipment_id="CAM-001",
            type="defect_rate",
            severity="warning",
            error_code="W-QC-RATE-HIGH",
            message="불량률 상승 감지 - 현재 25% (기준: 10%)",
            abnormal_value="불량률 25.0%",
            zone="검사 구역",
            timestamp="2026-03-30T09:35:00",
            acknowledged=False,
        ),
        Alert(
            id="ALT-003",
            equipment_id="FRN-001",
            type="process_delay",
            severity="warning",
            error_code="W-MELT-DELAY",
            message="용해 공정 지연 - 예상 시간 초과 15분",
            abnormal_value="지연 15분",
            zone="용해 구역",
            timestamp="2026-03-30T09:20:00",
            acknowledged=True,
        ),
        Alert(
            id="ALT-004",
            equipment_id="FRN-002",
            type="system",
            severity="info",
            error_code="I-SYS-MAINT",
            message="정기 점검 예정 - 용해로 #2 (2026-04-01)",
            abnormal_value="",
            zone="용해 구역",
            timestamp="2026-03-30T08:00:00",
            acknowledged=True,
        ),
        Alert(
            id="ALT-005",
            equipment_id="AMR-001",
            type="transport_failure",
            severity="warning",
            error_code="W-AMR-OBSTACLE",
            message="이송 경로 장애물 감지 - AMR #1 우회 경로 사용",
            abnormal_value="장애물 거리 0.3m",
            zone="이송 구역",
            timestamp="2026-03-30T09:18:00",
            acknowledged=True,
        ),
    ]
    db.add_all(rows)
    db.commit()


# ────────────────────────────────────────
# 9. 생산 통계
# ────────────────────────────────────────


def _seed_production_metrics(db: Session) -> None:
    if db.query(ProductionMetric).count() > 0:
        return
    metrics_data = [
        ("03/01", 45, 2, 4.4),
        ("03/02", 0, 0, 0.0),
        ("03/03", 52, 3, 5.8),
        ("03/04", 58, 2, 3.4),
        ("03/05", 61, 4, 6.6),
        ("03/06", 55, 1, 1.8),
        ("03/07", 49, 2, 4.1),
        ("03/08", 43, 3, 7.0),
        ("03/09", 0, 0, 0.0),
        ("03/10", 57, 2, 3.5),
        ("03/11", 63, 5, 7.9),
        ("03/12", 60, 3, 5.0),
        ("03/13", 65, 2, 3.1),
        ("03/14", 58, 1, 1.7),
        ("03/15", 50, 2, 4.0),
        ("03/16", 0, 0, 0.0),
        ("03/17", 54, 3, 5.6),
        ("03/18", 62, 2, 3.2),
        ("03/19", 59, 4, 6.8),
        ("03/20", 66, 2, 3.0),
        ("03/21", 64, 1, 1.6),
        ("03/22", 48, 2, 4.2),
        ("03/23", 0, 0, 0.0),
        ("03/24", 42, 2, 4.8),
        ("03/25", 55, 3, 5.5),
        ("03/26", 48, 1, 2.1),
        ("03/27", 61, 2, 3.3),
        ("03/28", 38, 3, 7.9),
        ("03/29", 52, 2, 3.8),
        ("03/30", 47, 2, 4.3),
    ]
    rows = [
        ProductionMetric(date=d, production=p, defects=def_, defect_rate=dr)
        for d, p, def_, dr in metrics_data
    ]
    db.add_all(rows)
    db.commit()
