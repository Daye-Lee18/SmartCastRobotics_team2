import type {
  Order,
  OrderDetail,
  Product,
  ProcessStageData,
  Equipment,
  TransportTask,
  InspectionRecord,
  Alert,
  DashboardStats,
  ProductionMetric,
  HourlyProduction,
  DefectTypeStat,
  MonthlyProductionSummary,
  WarehouseRack,
  OutboundOrder,
  InspectionStandard,
  SorterLog,
} from "./types";

// ────────────────────────────────────────
// 1. 주문 관리
// ────────────────────────────────────────

export const mockOrders: Order[] = [
  {
    id: "ORD-2026-001",
    customerId: "CUST-001",
    customerName: "김철수",
    companyName: "(주)한국도로공사",
    contact: "02-1234-5678",
    email: "customer1@example.com",
    shippingAddress: "서울특별시 성동구 용답동 123-4",
    totalAmount: 4250000,
    status: "in_production",
    requestedDelivery: "2026-04-15",
    confirmedDelivery: "2026-04-12",
    createdAt: "2026-03-25T09:00:00",
    updatedAt: "2026-03-28T14:30:00",
    shippedAt: "",
  },
  {
    id: "ORD-2026-002",
    customerId: "CUST-002",
    customerName: "이영희",
    companyName: "(주)서울시설공단",
    contact: "02-2345-6789",
    email: "customer2@example.com",
    shippingAddress: "서울특별시 중구 세종대로 110",
    totalAmount: 3600000,
    status: "approved",
    requestedDelivery: "2026-04-20",
    confirmedDelivery: "2026-04-18",
    createdAt: "2026-03-26T10:00:00",
    updatedAt: "2026-03-27T11:00:00",
    shippedAt: "",
  },
  {
    id: "ORD-2026-003",
    customerId: "CUST-003",
    customerName: "박민수",
    companyName: "(주)대한건설",
    contact: "031-345-6789",
    email: "customer3@example.com",
    shippingAddress: "경기도 수원시 장안구 정조로 123",
    totalAmount: 5500000,
    status: "pending",
    requestedDelivery: "2026-05-01",
    confirmedDelivery: "",
    createdAt: "2026-03-29T08:30:00",
    updatedAt: "2026-03-29T08:30:00",
    shippedAt: "",
  },
  {
    id: "ORD-2026-004",
    customerId: "CUST-004",
    customerName: "정수빈",
    companyName: "(주)경기도시공사",
    contact: "031-456-7890",
    email: "customer4@example.com",
    shippingAddress: "경기도 성남시 분당구 정자동 45-6",
    totalAmount: 1700000,
    status: "completed",
    requestedDelivery: "2026-03-28",
    confirmedDelivery: "2026-03-27",
    createdAt: "2026-03-15T09:00:00",
    updatedAt: "2026-03-27T16:00:00",
    shippedAt: "",
  },
  {
    id: "ORD-2026-005",
    customerId: "CUST-005",
    customerName: "최동현",
    companyName: "(주)부산항만공사",
    contact: "051-567-8901",
    email: "customer5@example.com",
    shippingAddress: "부산광역시 중구 충장대로 206",
    totalAmount: 7000000,
    status: "pending",
    requestedDelivery: "2026-04-25",
    confirmedDelivery: "",
    createdAt: "2026-03-30T07:00:00",
    updatedAt: "2026-03-30T07:00:00",
    shippedAt: "",
  },
];

export const mockOrderDetails: OrderDetail[] = [
  // ORD-2026-001 상세
  {
    id: "OD-001",
    orderId: "ORD-2026-001",
    productId: "PRD-001",
    productName: "맨홀 뚜껑 KS D-600",
    quantity: 50,
    spec: "600mm / 두께 50mm / EN124 D400",
    material: "GCD450 (구상흑연주철)",
    postProcessing: "표면 연마 + 방청 코팅",
    logoData: "한국도로공사 로고",
    unitPrice: 85000,
    subtotal: 4250000,
  },
  // ORD-2026-002 상세
  {
    id: "OD-002",
    orderId: "ORD-2026-002",
    productId: "PRD-002",
    productName: "맨홀 뚜껑 KS D-800",
    quantity: 30,
    spec: "800mm / 두께 60mm / EN124 E600",
    material: "GCD500 (구상흑연주철)",
    postProcessing: "표면 연마",
    logoData: "",
    unitPrice: 120000,
    subtotal: 3600000,
  },
  // ORD-2026-003 상세
  {
    id: "OD-003",
    orderId: "ORD-2026-003",
    productId: "PRD-003",
    productName: "맨홀 뚜껑 KS D-450",
    quantity: 100,
    spec: "450mm / 두께 40mm / EN124 C250",
    material: "FC250 (회주철)",
    postProcessing: "방청 코팅",
    logoData: "",
    unitPrice: 55000,
    subtotal: 5500000,
  },
  // ORD-2026-004 상세
  {
    id: "OD-004",
    orderId: "ORD-2026-004",
    productId: "PRD-001",
    productName: "맨홀 뚜껑 KS D-600",
    quantity: 20,
    spec: "600mm / 두께 50mm / EN124 D400",
    material: "GCD450 (구상흑연주철)",
    postProcessing: "표면 연마 + 방청 코팅 + 문구 삽입",
    logoData: "경기도시공사 문구",
    unitPrice: 85000,
    subtotal: 1700000,
  },
  // ORD-2026-005 상세
  {
    id: "OD-005",
    orderId: "ORD-2026-005",
    productId: "PRD-005",
    productName: "배수구 그레이팅",
    quantity: 200,
    spec: "500x300mm / 두께 30mm",
    material: "FC200 (회주철)",
    postProcessing: "아연 도금",
    logoData: "",
    unitPrice: 35000,
    subtotal: 7000000,
  },
];

export const mockProducts: Product[] = [
  {
    id: "PRD-001",
    name: "맨홀 뚜껑 KS D-600",
    category: "맨홀 뚜껑",
    basePrice: 85000,
    optionPricing: { "표면 연마": 5000, "방청 코팅": 3000, "로고 삽입": 8000 },
    designImageUrl: "/images/products/manhole-600.png",
    model3dPath: "/models/manhole-600.glb",
  },
  {
    id: "PRD-002",
    name: "맨홀 뚜껑 KS D-800",
    category: "맨홀 뚜껑",
    basePrice: 120000,
    optionPricing: { "표면 연마": 7000, "방청 코팅": 4000, "로고 삽입": 10000 },
    designImageUrl: "/images/products/manhole-800.png",
    model3dPath: "/models/manhole-800.glb",
  },
  {
    id: "PRD-003",
    name: "맨홀 뚜껑 KS D-450",
    category: "맨홀 뚜껑",
    basePrice: 55000,
    optionPricing: { "표면 연마": 3000, "방청 코팅": 2000 },
    designImageUrl: "/images/products/manhole-450.png",
    model3dPath: "/models/manhole-450.glb",
  },
  {
    id: "PRD-004",
    name: "빗물받이 KS D-300",
    category: "빗물받이",
    basePrice: 42000,
    optionPricing: { "방청 코팅": 2500, "아연 도금": 6000 },
    designImageUrl: "/images/products/drain-300.png",
    model3dPath: "/models/drain-300.glb",
  },
  {
    id: "PRD-005",
    name: "배수구 그레이팅",
    category: "그레이팅",
    basePrice: 35000,
    optionPricing: { "아연 도금": 5000, "내식 코팅": 7000 },
    designImageUrl: "/images/products/grating-500.png",
    model3dPath: "/models/grating-500.glb",
  },
];

// ────────────────────────────────────────
// 2. 생산 모니터링
// ────────────────────────────────────────

export const mockProcessStages: ProcessStageData[] = [
  {
    stage: "melting",
    label: "용해",
    status: "running",
    temperature: 1420,
    targetTemperature: 1450,
    progress: 85,
    startTime: "2026-03-30T08:00:00",
    estimatedEnd: "2026-03-30T09:30:00",
    equipmentId: "FRN-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0301",
    heatingPower: 92,
  },
  {
    stage: "molding",
    label: "주형 제작",
    status: "completed",
    progress: 100,
    startTime: "2026-03-30T07:00:00",
    estimatedEnd: "2026-03-30T08:00:00",
    equipmentId: "MLD-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0301",
    pressure: 85,
  },
  {
    stage: "pouring",
    label: "주탕",
    status: "waiting",
    temperature: 1400,
    targetTemperature: 1400,
    progress: 0,
    equipmentId: "ARM-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0301",
    pourAngle: 45,
  },
  {
    stage: "cooling",
    label: "냉각",
    status: "running",
    temperature: 320,
    targetTemperature: 25,
    progress: 60,
    startTime: "2026-03-30T06:00:00",
    estimatedEnd: "2026-03-30T10:00:00",
    equipmentId: "CLZ-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0300",
    coolingProgress: 60,
  },
  {
    stage: "demolding",
    label: "탈형",
    status: "idle",
    progress: 0,
    equipmentId: "ARM-002",
    orderId: "ORD-2026-001",
    jobId: "JOB-0300",
  },
  {
    stage: "post_processing",
    label: "후처리",
    status: "running",
    progress: 45,
    startTime: "2026-03-30T09:00:00",
    estimatedEnd: "2026-03-30T10:30:00",
    equipmentId: "ARM-003",
    orderId: "ORD-2026-001",
    jobId: "JOB-0299",
  },
  {
    stage: "inspection",
    label: "검사",
    status: "running",
    progress: 70,
    startTime: "2026-03-30T09:30:00",
    estimatedEnd: "2026-03-30T10:00:00",
    equipmentId: "CAM-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0298",
  },
  {
    stage: "classification",
    label: "분류",
    status: "idle",
    progress: 0,
    equipmentId: "SRT-001",
    orderId: "ORD-2026-001",
    jobId: "JOB-0298",
  },
];

// ────────────────────────────────────────
// 3. 설비 관리
// ────────────────────────────────────────

export const mockEquipment: Equipment[] = [
  { id: "FRN-001", name: "용해로 #1", type: "furnace", commId: "192.168.1.101", installLocation: "용해 구역 A동", status: "running", posX: 2.0, posY: 1.0, posZ: 0.0, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-20", operatingHours: 1250, errorCount: 0 },
  { id: "FRN-002", name: "용해로 #2", type: "furnace", commId: "192.168.1.102", installLocation: "용해 구역 A동", status: "idle", posX: 4.0, posY: 1.0, posZ: 0.0, lastUpdate: "2026-03-30T09:45:00", lastMaintenance: "2026-03-18", operatingHours: 980, errorCount: 1 },
  { id: "MLD-001", name: "조형기 #1", type: "mold_press", commId: "192.168.1.110", installLocation: "주형 구역 B동", status: "running", posX: 8.0, posY: 1.0, posZ: 0.0, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-22", operatingHours: 890, errorCount: 0 },
  { id: "ARM-001", name: "로봇암 #1 (주탕)", type: "robot_arm", commId: "192.168.1.120", installLocation: "주조 구역 C동", status: "idle", posX: 12.0, posY: 2.0, posZ: 0.0, lastUpdate: "2026-03-30T09:50:00", lastMaintenance: "2026-03-25", operatingHours: 650, errorCount: 0 },
  { id: "ARM-002", name: "로봇암 #2 (탈형)", type: "robot_arm", commId: "192.168.1.121", installLocation: "냉각 구역 D동", status: "idle", posX: 16.0, posY: 2.0, posZ: 0.0, lastUpdate: "2026-03-30T09:48:00", lastMaintenance: "2026-03-24", operatingHours: 720, errorCount: 2 },
  { id: "ARM-003", name: "로봇암 #3 (후처리)", type: "robot_arm", commId: "192.168.1.122", installLocation: "후처리 구역 E동", status: "running", posX: 20.0, posY: 2.0, posZ: 0.0, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-26", operatingHours: 540, errorCount: 0 },
  { id: "AMR-001", name: "AMR #1", type: "amr", commId: "ros2://amr_01/cmd_vel", installLocation: "이송 구역", status: "running", posX: 14.0, posY: 5.0, posZ: 0.0, battery: 78, speed: 1.2, lastUpdate: "2026-03-30T10:01:00", lastMaintenance: "2026-03-28", operatingHours: 320, errorCount: 0 },
  { id: "AMR-002", name: "AMR #2", type: "amr", commId: "ros2://amr_02/cmd_vel", installLocation: "대기 장소", status: "idle", posX: 6.0, posY: 8.0, posZ: 0.0, battery: 95, speed: 0.0, lastUpdate: "2026-03-30T09:55:00", lastMaintenance: "2026-03-27", operatingHours: 280, errorCount: 0 },
  { id: "AMR-003", name: "AMR #3", type: "amr", commId: "ros2://amr_03/cmd_vel", installLocation: "충전소", status: "charging", posX: 1.0, posY: 8.0, posZ: 0.0, battery: 12, speed: 0.0, lastUpdate: "2026-03-30T09:40:00", lastMaintenance: "2026-03-29", operatingHours: 410, errorCount: 1 },
  { id: "CVR-001", name: "컨베이어 #1", type: "conveyor", commId: "192.168.1.130", installLocation: "검사 구역 F동", status: "running", posX: 24.0, posY: 3.0, posZ: 0.0, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-21", operatingHours: 1100, errorCount: 0 },
  { id: "CAM-001", name: "검사 카메라 #1", type: "camera", commId: "192.168.1.140", installLocation: "검사 구역 F동", status: "running", posX: 25.0, posY: 3.0, posZ: 1.5, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-23", operatingHours: 800, errorCount: 0 },
  { id: "SRT-001", name: "분류기 #1", type: "sorter", commId: "192.168.1.150", installLocation: "분류 구역 F동", status: "running", posX: 28.0, posY: 3.0, posZ: 0.0, lastUpdate: "2026-03-30T10:00:00", lastMaintenance: "2026-03-19", operatingHours: 950, errorCount: 0 },
];

// ────────────────────────────────────────
// 4. 이송 / 물류
// ────────────────────────────────────────

export const mockTransports: TransportTask[] = [
  { id: "TRN-001", fromName: "주조 구역 C동", fromCoord: "12,2", toName: "후처리 구역 E동", toCoord: "20,2", itemId: "CST-0301-B1", itemName: "주물 팔레트", quantity: 5, priority: "high", status: "moving_to_dest", assignedRobotId: "AMR-001", requestedAt: "2026-03-30T09:15:00" },
  { id: "TRN-002", fromName: "후처리 구역 E동", fromCoord: "20,2", toName: "검사 구역 F동", toCoord: "24,3", itemId: "CST-0300-PP", itemName: "후처리 완료 주물", quantity: 3, priority: "medium", status: "unassigned", assignedRobotId: "", requestedAt: "2026-03-30T09:30:00" },
  { id: "TRN-003", fromName: "검사 구역 F동", fromCoord: "24,3", toName: "적재 구역 G동", toCoord: "30,5", itemId: "CST-0298-OK", itemName: "양품 팔레트", quantity: 10, priority: "medium", status: "completed", assignedRobotId: "AMR-002", requestedAt: "2026-03-30T08:00:00", completedAt: "2026-03-30T08:25:00" },
  { id: "TRN-004", fromName: "검사 구역 F동", fromCoord: "24,3", toName: "폐기물 구역 H동", toCoord: "32,8", itemId: "CST-0298-NG", itemName: "불량품 박스", quantity: 2, priority: "low", status: "completed", assignedRobotId: "AMR-001", requestedAt: "2026-03-30T08:30:00", completedAt: "2026-03-30T08:45:00" },
  { id: "TRN-005", fromName: "적재 구역 G동", fromCoord: "30,5", toName: "출하 구역 I동", toCoord: "34,1", itemId: "CST-0295-SHP", itemName: "출고 팔레트", quantity: 8, priority: "high", status: "assigned", assignedRobotId: "AMR-002", requestedAt: "2026-03-30T09:45:00" },
];

// ────────────────────────────────────────
// 5. 창고 랙 (WarehouseRack)
// ────────────────────────────────────────

const rackStatuses: WarehouseRack["status"][] = [
  "occupied", "empty", "occupied", "reserved", "empty", "occupied",
  "occupied", "empty", "unavailable", "occupied", "empty", "occupied",
  "occupied", "occupied", "empty", "empty", "occupied", "reserved",
  "empty", "occupied", "empty", "empty", "occupied", "occupied",
];

const rackItems: { itemId: string; itemName: string; quantity: number }[] = [
  { itemId: "PRD-001", itemName: "맨홀 뚜껑 KS D-600", quantity: 8 },
  { itemId: "PRD-002", itemName: "맨홀 뚜껑 KS D-800", quantity: 4 },
  { itemId: "PRD-003", itemName: "맨홀 뚜껑 KS D-450", quantity: 12 },
  { itemId: "PRD-004", itemName: "빗물받이 KS D-300", quantity: 6 },
  { itemId: "PRD-005", itemName: "배수구 그레이팅", quantity: 15 },
  { itemId: "PRD-001", itemName: "맨홀 뚜껑 KS D-600", quantity: 5 },
  { itemId: "PRD-002", itemName: "맨홀 뚜껑 KS D-800", quantity: 3 },
  { itemId: "PRD-003", itemName: "맨홀 뚜껑 KS D-450", quantity: 10 },
  { itemId: "PRD-005", itemName: "배수구 그레이팅", quantity: 7 },
  { itemId: "PRD-001", itemName: "맨홀 뚜껑 KS D-600", quantity: 9 },
  { itemId: "PRD-004", itemName: "빗물받이 KS D-300", quantity: 4 },
  { itemId: "PRD-003", itemName: "맨홀 뚜껑 KS D-450", quantity: 6 },
  { itemId: "PRD-005", itemName: "배수구 그레이팅", quantity: 11 },
  { itemId: "PRD-002", itemName: "맨홀 뚜껑 KS D-800", quantity: 2 },
];

export const mockWarehouseRacks: WarehouseRack[] = Array.from({ length: 24 }, (_, i) => {
  const row = Math.floor(i / 6) + 1;
  const col = (i % 6) + 1;
  const status = rackStatuses[i];
  const rack: WarehouseRack = {
    id: `RCK-${String(row).padStart(2, "0")}-${String(col).padStart(2, "0")}`,
    zone: row <= 2 ? "A구역" : "B구역",
    rackNumber: `${String(row).padStart(2, "0")}-${String(col).padStart(2, "0")}`,
    status,
    row,
    col,
  };
  if (status === "occupied" || status === "reserved") {
    const itemIdx = i % rackItems.length;
    rack.itemId = rackItems[itemIdx].itemId;
    rack.itemName = rackItems[itemIdx].itemName;
    rack.quantity = rackItems[itemIdx].quantity;
    rack.lastInboundAt = "2026-03-30T09:00:00";
  }
  return rack;
});

// ────────────────────────────────────────
// 6. 출고 주문
// ────────────────────────────────────────

export const mockOutboundOrders: OutboundOrder[] = [
  { id: "OUT-001", productId: "PRD-001", productName: "맨홀 뚜껑 KS D-600", quantity: 20, destination: "(주)경기도시공사", policy: "FIFO", completed: true, createdAt: "2026-03-27T10:00:00" },
  { id: "OUT-002", productId: "PRD-002", productName: "맨홀 뚜껑 KS D-800", quantity: 10, destination: "(주)서울시설공단", policy: "FIFO", completed: false, createdAt: "2026-03-30T08:00:00" },
  { id: "OUT-003", productId: "PRD-005", productName: "배수구 그레이팅", quantity: 50, destination: "(주)부산항만공사", policy: "LIFO", completed: false, createdAt: "2026-03-30T09:00:00" },
  { id: "OUT-004", productId: "PRD-003", productName: "맨홀 뚜껑 KS D-450", quantity: 30, destination: "(주)대한건설", policy: "FIFO", completed: false, createdAt: "2026-03-30T11:00:00" },
  { id: "OUT-005", productId: "PRD-004", productName: "빗물받이 KS D-300", quantity: 15, destination: "(주)인천항만공사", policy: "FIFO", completed: true, createdAt: "2026-03-28T14:00:00" },
];

// ────────────────────────────────────────
// 7. 품질 검사
// ────────────────────────────────────────

export const mockInspections: InspectionRecord[] = [
  // ORD-2026-004 검사 기록
  { id: "INS-001", productId: "PRD-001", castingId: "CST-0298-01", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 98.5, inspectorId: "CAM-001", imageId: "IMG-001", inspectedAt: "2026-03-30T09:31:00" },
  { id: "INS-002", productId: "PRD-001", castingId: "CST-0298-02", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 97.2, inspectorId: "CAM-001", imageId: "IMG-002", inspectedAt: "2026-03-30T09:32:00" },
  { id: "INS-003", productId: "PRD-001", castingId: "CST-0298-03", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D01", confidence: 95.8, inspectorId: "CAM-001", imageId: "IMG-003", inspectedAt: "2026-03-30T09:33:00", defectType: "표면 균열", defectDetail: "뚜껑 외곽부 0.3mm 크랙" },
  { id: "INS-004", productId: "PRD-001", castingId: "CST-0298-04", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 99.1, inspectorId: "CAM-001", imageId: "IMG-004", inspectedAt: "2026-03-30T09:34:00" },
  { id: "INS-005", productId: "PRD-001", castingId: "CST-0298-05", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 96.7, inspectorId: "CAM-001", imageId: "IMG-005", inspectedAt: "2026-03-30T09:35:00" },
  { id: "INS-006", productId: "PRD-001", castingId: "CST-0298-06", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D02", confidence: 94.3, inspectorId: "CAM-001", imageId: "IMG-006", inspectedAt: "2026-03-30T09:36:00", defectType: "기포 불량", defectDetail: "내부 기포 2개 감지 (직경 1.5mm)" },
  { id: "INS-007", productId: "PRD-001", castingId: "CST-0298-07", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 98.0, inspectorId: "CAM-001", imageId: "IMG-007", inspectedAt: "2026-03-30T09:37:00" },
  { id: "INS-008", productId: "PRD-001", castingId: "CST-0298-08", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 97.5, inspectorId: "CAM-001", imageId: "IMG-008", inspectedAt: "2026-03-30T09:38:00" },
  // ORD-2026-001 검사 기록 (생산 중)
  { id: "INS-009", productId: "PRD-001", castingId: "CST-0301-01", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 98.8, inspectorId: "CAM-001", imageId: "IMG-009", inspectedAt: "2026-03-30T10:01:00" },
  { id: "INS-010", productId: "PRD-001", castingId: "CST-0301-02", orderId: "ORD-2026-001", result: "fail", defectTypeCode: "D03", confidence: 92.1, inspectorId: "CAM-001", imageId: "IMG-010", inspectedAt: "2026-03-30T10:02:30", defectType: "수축 결함", defectDetail: "중앙부 수축 3mm 초과" },
  { id: "INS-011", productId: "PRD-001", castingId: "CST-0301-03", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 97.9, inspectorId: "CAM-001", imageId: "IMG-011", inspectedAt: "2026-03-30T10:04:00" },
  { id: "INS-012", productId: "PRD-001", castingId: "CST-0301-04", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 99.3, inspectorId: "CAM-001", imageId: "IMG-012", inspectedAt: "2026-03-30T10:05:30" },
  { id: "INS-013", productId: "PRD-001", castingId: "CST-0301-05", orderId: "ORD-2026-001", result: "fail", defectTypeCode: "D01", confidence: 96.4, inspectorId: "CAM-001", imageId: "IMG-013", inspectedAt: "2026-03-30T10:07:00", defectType: "표면 균열", defectDetail: "테두리 미세 균열 0.2mm" },
  { id: "INS-014", productId: "PRD-001", castingId: "CST-0301-06", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 98.2, inspectorId: "CAM-001", imageId: "IMG-014", inspectedAt: "2026-03-30T10:08:30" },
  { id: "INS-015", productId: "PRD-001", castingId: "CST-0301-07", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 97.0, inspectorId: "CAM-001", imageId: "IMG-015", inspectedAt: "2026-03-30T10:10:00" },
  { id: "INS-016", productId: "PRD-001", castingId: "CST-0301-08", orderId: "ORD-2026-001", result: "fail", defectTypeCode: "D06", confidence: 93.7, inspectorId: "CAM-001", imageId: "IMG-016", inspectedAt: "2026-03-30T10:11:30", defectType: "주탕 불량", defectDetail: "미충전 부위 발생" },
  { id: "INS-017", productId: "PRD-001", castingId: "CST-0301-09", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 98.6, inspectorId: "CAM-001", imageId: "IMG-017", inspectedAt: "2026-03-30T10:13:00" },
  { id: "INS-018", productId: "PRD-001", castingId: "CST-0301-10", orderId: "ORD-2026-001", result: "pass", defectTypeCode: "", confidence: 99.0, inspectorId: "CAM-001", imageId: "IMG-018", inspectedAt: "2026-03-30T10:14:30" },
  // 이전 주문 검사 기록 (다양한 불량 유형)
  { id: "INS-019", productId: "PRD-001", castingId: "CST-0295-01", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D04", confidence: 91.5, inspectorId: "CAM-001", imageId: "IMG-019", inspectedAt: "2026-03-29T14:20:00", defectType: "치수 불량", defectDetail: "외경 601.5mm (허용 +-0.5mm)" },
  { id: "INS-020", productId: "PRD-001", castingId: "CST-0295-02", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 98.3, inspectorId: "CAM-001", imageId: "IMG-020", inspectedAt: "2026-03-29T14:21:30" },
  { id: "INS-021", productId: "PRD-001", castingId: "CST-0295-03", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D02", confidence: 89.8, inspectorId: "CAM-001", imageId: "IMG-021", inspectedAt: "2026-03-29T14:23:00", defectType: "기포 불량", defectDetail: "표면 기포 다수 (5개 이상)" },
  { id: "INS-022", productId: "PRD-001", castingId: "CST-0295-04", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 97.6, inspectorId: "CAM-001", imageId: "IMG-022", inspectedAt: "2026-03-29T14:24:30" },
  { id: "INS-023", productId: "PRD-001", castingId: "CST-0295-05", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D05", confidence: 93.2, inspectorId: "CAM-001", imageId: "IMG-023", inspectedAt: "2026-03-29T14:26:00", defectType: "냉각 균열", defectDetail: "급속 냉각 열응력 균열" },
  { id: "INS-024", productId: "PRD-001", castingId: "CST-0295-06", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 99.4, inspectorId: "CAM-001", imageId: "IMG-024", inspectedAt: "2026-03-29T14:27:30" },
  { id: "INS-025", productId: "PRD-001", castingId: "CST-0295-07", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D07", confidence: 90.1, inspectorId: "CAM-001", imageId: "IMG-025", inspectedAt: "2026-03-29T14:29:00", defectType: "주형 결함", defectDetail: "주형 파손에 의한 형상 이상" },
  { id: "INS-026", productId: "PRD-001", castingId: "CST-0295-08", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 96.9, inspectorId: "CAM-001", imageId: "IMG-026", inspectedAt: "2026-03-29T14:30:30" },
  { id: "INS-027", productId: "PRD-001", castingId: "CST-0295-09", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D01", confidence: 88.7, inspectorId: "CAM-001", imageId: "IMG-027", inspectedAt: "2026-03-29T14:32:00", defectType: "표면 균열", defectDetail: "하부면 균열 0.5mm" },
  { id: "INS-028", productId: "PRD-001", castingId: "CST-0295-10", orderId: "ORD-2026-004", result: "pass", defectTypeCode: "", confidence: 98.1, inspectorId: "CAM-001", imageId: "IMG-028", inspectedAt: "2026-03-29T14:33:30" },
  { id: "INS-029", productId: "PRD-001", castingId: "CST-0296-01", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D03", confidence: 91.9, inspectorId: "CAM-001", imageId: "IMG-029", inspectedAt: "2026-03-29T15:10:00", defectType: "수축 결함", defectDetail: "냉각 수축률 기준 초과" },
  { id: "INS-030", productId: "PRD-001", castingId: "CST-0296-02", orderId: "ORD-2026-004", result: "fail", defectTypeCode: "D02", confidence: 87.3, inspectorId: "CAM-001", imageId: "IMG-030", inspectedAt: "2026-03-29T15:11:30", defectType: "기포 불량", defectDetail: "내부 기포 밀집 구간" },
];

export const mockInspectionStandards: InspectionStandard[] = [
  { productId: "PRD-001", productName: "맨홀 뚜껑 KS D-600", toleranceRange: "+-0.5mm", targetDimension: "외경 600mm / 두께 50mm", threshold: 95.0 },
  { productId: "PRD-002", productName: "맨홀 뚜껑 KS D-800", toleranceRange: "+-0.8mm", targetDimension: "외경 800mm / 두께 60mm", threshold: 95.0 },
  { productId: "PRD-003", productName: "맨홀 뚜껑 KS D-450", toleranceRange: "+-0.4mm", targetDimension: "외경 450mm / 두께 40mm", threshold: 93.0 },
];

export const mockSorterLogs: SorterLog[] = [
  { inspectionId: "INS-001", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-002", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-003", sortDirection: "fail_line", sorterAngle: 45, success: true },
  { inspectionId: "INS-004", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-005", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-006", sortDirection: "fail_line", sorterAngle: 45, success: true },
  { inspectionId: "INS-007", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-008", sortDirection: "pass_line", sorterAngle: 0, success: false },
  { inspectionId: "INS-009", sortDirection: "pass_line", sorterAngle: 0, success: true },
  { inspectionId: "INS-010", sortDirection: "fail_line", sorterAngle: 45, success: true },
];

// ────────────────────────────────────────
// 8. 알림
// ────────────────────────────────────────

export const mockAlerts: Alert[] = [
  { id: "ALT-001", equipmentId: "AMR-003", type: "equipment_error", severity: "critical", errorCode: "E-AMR-BAT-LOW", message: "AMR #3 배터리 부족 - 충전 필요 (12%)", abnormalValue: "배터리 12% (임계값 15%)", zone: "이송 구역", timestamp: "2026-03-30T09:40:00", acknowledged: false },
  { id: "ALT-002", equipmentId: "CAM-001", type: "defect_rate", severity: "warning", errorCode: "W-QC-RATE-HIGH", message: "불량률 상승 감지 - 현재 25% (기준: 10%)", abnormalValue: "불량률 25.0%", zone: "검사 구역", timestamp: "2026-03-30T09:35:00", acknowledged: false },
  { id: "ALT-003", equipmentId: "FRN-001", type: "process_delay", severity: "warning", errorCode: "W-MELT-DELAY", message: "용해 공정 지연 - 예상 시간 초과 15분", abnormalValue: "지연 15분", zone: "용해 구역", timestamp: "2026-03-30T09:20:00", acknowledged: true },
  { id: "ALT-004", equipmentId: "FRN-002", type: "system", severity: "info", errorCode: "I-SYS-MAINT", message: "정기 점검 예정 - 용해로 #2 (2026-04-01)", abnormalValue: "", zone: "용해 구역", timestamp: "2026-03-30T08:00:00", acknowledged: true },
  { id: "ALT-005", equipmentId: "AMR-001", type: "transport_failure", severity: "warning", errorCode: "W-AMR-OBSTACLE", message: "이송 경로 장애물 감지 - AMR #1 우회 경로 사용", abnormalValue: "장애물 거리 0.3m", zone: "이송 구역", timestamp: "2026-03-30T09:18:00", acknowledged: true },
];

// ────────────────────────────────────────
// 9. 대시보드 통계
// ────────────────────────────────────────

export const mockDashboardStats: DashboardStats = {
  productionGoalRate: 78.3,
  activeRobots: 4,
  pendingOrders: 2,
  todayAlarms: 5,
  todayProduction: 47,
  defectRate: 4.2,
  equipmentUtilization: 72.5,
  completedToday: 15,
};

// ────────────────────────────────────────
// 10. 차트/통계 데이터
// ────────────────────────────────────────

// 30일간 생산 추이 데이터 (현실적인 주물 공장 생산량 시뮬레이션)
export const mockProductionMetrics: ProductionMetric[] = [
  { date: "03/01", production: 45, defects: 2, defectRate: 4.4 },
  { date: "03/02", production: 0, defects: 0, defectRate: 0 },   // 일요일 - 휴무
  { date: "03/03", production: 52, defects: 3, defectRate: 5.8 },
  { date: "03/04", production: 58, defects: 2, defectRate: 3.4 },
  { date: "03/05", production: 61, defects: 4, defectRate: 6.6 },
  { date: "03/06", production: 55, defects: 1, defectRate: 1.8 },
  { date: "03/07", production: 49, defects: 2, defectRate: 4.1 },
  { date: "03/08", production: 43, defects: 3, defectRate: 7.0 },
  { date: "03/09", production: 0, defects: 0, defectRate: 0 },   // 일요일 - 휴무
  { date: "03/10", production: 57, defects: 2, defectRate: 3.5 },
  { date: "03/11", production: 63, defects: 5, defectRate: 7.9 }, // 용해로 정비 후 초기 불량 증가
  { date: "03/12", production: 60, defects: 3, defectRate: 5.0 },
  { date: "03/13", production: 65, defects: 2, defectRate: 3.1 },
  { date: "03/14", production: 58, defects: 1, defectRate: 1.7 },
  { date: "03/15", production: 50, defects: 2, defectRate: 4.0 },
  { date: "03/16", production: 0, defects: 0, defectRate: 0 },   // 일요일 - 휴무
  { date: "03/17", production: 54, defects: 3, defectRate: 5.6 },
  { date: "03/18", production: 62, defects: 2, defectRate: 3.2 },
  { date: "03/19", production: 59, defects: 4, defectRate: 6.8 }, // 새 패턴 적용 초기
  { date: "03/20", production: 66, defects: 2, defectRate: 3.0 },
  { date: "03/21", production: 64, defects: 1, defectRate: 1.6 },
  { date: "03/22", production: 48, defects: 2, defectRate: 4.2 },
  { date: "03/23", production: 0, defects: 0, defectRate: 0 },   // 일요일 - 휴무
  { date: "03/24", production: 42, defects: 2, defectRate: 4.8 },
  { date: "03/25", production: 55, defects: 3, defectRate: 5.5 },
  { date: "03/26", production: 48, defects: 1, defectRate: 2.1 },
  { date: "03/27", production: 61, defects: 2, defectRate: 3.3 },
  { date: "03/28", production: 38, defects: 3, defectRate: 7.9 }, // 원자재 공급 지연
  { date: "03/29", production: 52, defects: 2, defectRate: 3.8 },
  { date: "03/30", production: 47, defects: 2, defectRate: 4.3 },
];

// 최근 7일 데이터 (대시보드 메인에서 사용)
export const mockWeeklyMetrics: ProductionMetric[] = mockProductionMetrics.slice(-7);

// 시간대별 오늘 생산량 (생산 모니터링에서 사용)
export const mockHourlyProduction: HourlyProduction[] = [
  { hour: "06:00", production: 0, defects: 0, temperature: 25 },
  { hour: "07:00", production: 3, defects: 0, temperature: 850 },
  { hour: "08:00", production: 7, defects: 0, temperature: 1380 },
  { hour: "09:00", production: 12, defects: 1, temperature: 1420 },
  { hour: "10:00", production: 8, defects: 0, temperature: 1445 },
  { hour: "11:00", production: 6, defects: 1, temperature: 1430 },
  { hour: "12:00", production: 2, defects: 0, temperature: 1200 },  // 점심
  { hour: "13:00", production: 5, defects: 0, temperature: 1410 },
  { hour: "14:00", production: 4, defects: 0, temperature: 1440 },
];

// 월별 불량 유형 집계 (품질 검사 페이지에서 사용)
export const mockDefectTypeStats: DefectTypeStat[] = [
  { type: "표면 균열", count: 12, percentage: 28.6, color: "#ef4444" },
  { type: "기포 불량", count: 9, percentage: 21.4, color: "#f97316" },
  { type: "수축 결함", count: 7, percentage: 16.7, color: "#eab308" },
  { type: "치수 불량", count: 6, percentage: 14.3, color: "#22c55e" },
  { type: "냉각 균열", count: 4, percentage: 9.5, color: "#3b82f6" },
  { type: "주탕 불량", count: 2, percentage: 4.8, color: "#8b5cf6" },
  { type: "주형 결함", count: 2, percentage: 4.8, color: "#ec4899" },
];

// 월별 생산 요약 (대시보드에서 사용)
export const mockMonthlySummary: MonthlyProductionSummary[] = [
  { month: "2025/10", totalProduction: 1180, totalDefects: 52, defectRate: 4.4, ordersFulfilled: 12 },
  { month: "2025/11", totalProduction: 1250, totalDefects: 48, defectRate: 3.8, ordersFulfilled: 14 },
  { month: "2025/12", totalProduction: 980, totalDefects: 55, defectRate: 5.6, ordersFulfilled: 10 },
  { month: "2026/01", totalProduction: 1320, totalDefects: 42, defectRate: 3.2, ordersFulfilled: 15 },
  { month: "2026/02", totalProduction: 1150, totalDefects: 39, defectRate: 3.4, ordersFulfilled: 13 },
  { month: "2026/03", totalProduction: 1087, totalDefects: 47, defectRate: 4.3, ordersFulfilled: 11 },
];
