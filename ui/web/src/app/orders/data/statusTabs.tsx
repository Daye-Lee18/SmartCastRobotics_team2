import {
  CheckCircle,
  Clock,
  Factory,
  Package,
  PackageCheck,
  ThumbsUp,
  Truck,
} from "lucide-react";
import type { OrderStatus } from "@/lib/types";

export interface StatusTab {
  key: OrderStatus | "all";
  label: string;
  icon: React.ReactNode;
}

// 좌측 주문 목록 상단의 7개 상태 탭 정의.
export const STATUS_TABS: StatusTab[] = [
  { key: "all", label: "전체", icon: <Package size={15} /> },
  { key: "pending", label: "접수", icon: <Clock size={15} /> },
  { key: "approved", label: "승인", icon: <ThumbsUp size={15} /> },
  { key: "in_production", label: "생산", icon: <Factory size={15} /> },
  { key: "production_completed", label: "생산 완료", icon: <PackageCheck size={15} /> },
  { key: "shipping_ready", label: "출고", icon: <Truck size={15} /> },
  { key: "completed", label: "완료", icon: <CheckCircle size={15} /> },
];
