import {
  ArrowDownUp,
  ArrowRightLeft,
  Bot,
  Droplets,
  Flame,
  Layers,
  Truck,
  Video,
  Wind,
  Wrench,
} from "lucide-react";
import type {
  EquipmentStatus,
  EquipmentType,
  ProcessStage,
} from "@/lib/types";

export interface FlowStep {
  key: ProcessStage;
  label: string;
  icon: React.ReactNode;
}

// 5단계 공정 흐름 (용해 → 조형 → 주탕 → 냉각/탈형 → 후처리/검사).
export const PROCESS_FLOW: FlowStep[] = [
  { key: "melting", label: "원재료 투입 / 용해", icon: <Flame className="w-5 h-5" /> },
  { key: "molding", label: "조형", icon: <Layers className="w-5 h-5" /> },
  { key: "pouring", label: "주탕", icon: <Droplets className="w-5 h-5" /> },
  { key: "cooling", label: "냉각 / 탈형", icon: <Wind className="w-5 h-5" /> },
  { key: "post_processing", label: "후처리 / 검사", icon: <Wrench className="w-5 h-5" /> },
];

// 설비 타입별 아이콘.
export const equipmentTypeIcon: Record<EquipmentType, React.ReactNode> = {
  furnace: <Flame className="w-4 h-4" />,
  mold_press: <Layers className="w-4 h-4" />,
  robot_arm: <Bot className="w-4 h-4" />,
  amr: <Truck className="w-4 h-4" />,
  conveyor: <ArrowRightLeft className="w-4 h-4" />,
  camera: <Video className="w-4 h-4" />,
  sorter: <ArrowDownUp className="w-4 h-4" />,
};

// 설비 타입별 전환 가능한 상태 목록.
export const equipmentValidStates: Record<EquipmentType, EquipmentStatus[]> = {
  robot_arm: ["running", "idle", "maintenance"],
  amr: ["running", "idle", "charging", "maintenance"],
  furnace: ["running", "idle", "maintenance"],
  mold_press: ["running", "idle", "maintenance"],
  conveyor: ["running", "idle", "error"],
  camera: ["running", "idle"],
  sorter: ["running", "idle"],
};

// 상태 버튼 active/inactive 색상.
export const statusButtonStyle: Record<
  EquipmentStatus,
  { active: string; inactive: string }
> = {
  running: {
    active: "bg-green-500 text-white ring-2 ring-green-300 shadow-md",
    inactive: "bg-green-50 text-green-600 hover:bg-green-100 border border-green-200",
  },
  idle: {
    active: "bg-gray-500 text-white ring-2 ring-gray-300 shadow-md",
    inactive: "bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200",
  },
  charging: {
    active: "bg-blue-500 text-white ring-2 ring-blue-300 shadow-md",
    inactive: "bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200",
  },
  maintenance: {
    active: "bg-yellow-500 text-white ring-2 ring-yellow-300 shadow-md",
    inactive: "bg-yellow-50 text-yellow-600 hover:bg-yellow-100 border border-yellow-200",
  },
  error: {
    active: "bg-red-500 text-white ring-2 ring-red-300 shadow-md animate-pulse",
    inactive: "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200",
  },
};
