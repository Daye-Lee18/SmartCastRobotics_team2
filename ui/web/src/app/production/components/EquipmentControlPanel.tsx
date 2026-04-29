"use client";

import { BatteryMedium, MapPin, Settings } from "lucide-react";
import type { Equipment, EquipmentStatus } from "@/lib/types";
import { cn, equipmentStatusMap } from "@/lib/utils";
import {
  equipmentTypeIcon,
  equipmentValidStates,
  statusButtonStyle,
} from "../data/processFlow";

interface EquipmentControlPanelProps {
  equipmentList: Equipment[];
  equipmentStatuses: Record<string, EquipmentStatus>;
  autoModes: Record<string, boolean>;
  recentlyChanged: string | null;
  onToggleMode: (equipmentId: string) => void;
  onChangeStatus: (equipmentId: string, newStatus: EquipmentStatus) => void;
}

// 설비 제어 패널 — 각 설비 행에 자동/수동 토글 + 허용 상태 버튼 그룹.
// AMR 은 배터리 잔량 별도 표시.
export function EquipmentControlPanel({
  equipmentList,
  equipmentStatuses,
  autoModes,
  recentlyChanged,
  onToggleMode,
  onChangeStatus,
}: EquipmentControlPanelProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex-1 flex flex-col min-h-0">
      <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2 mb-4">
        <Settings className="w-5 h-5 text-gray-500" />
        설비 제어
      </h3>
      <div className="space-y-3 overflow-y-auto pr-1 flex-1 min-h-0">
        {equipmentList.map((eq) => {
          const currentStatus = equipmentStatuses[eq.id] ?? eq.status;
          const statusInfo = equipmentStatusMap[currentStatus];
          const isAuto = autoModes[eq.id] ?? true;
          const validStates = equipmentValidStates[eq.type] ?? ["running", "idle"];
          const isChanged = recentlyChanged === eq.id;

          return (
            <div
              key={eq.id}
              className={cn(
                "bg-gray-50 rounded-lg px-3 py-3 transition-all duration-300",
                isChanged && "ring-2 ring-blue-400 bg-blue-50"
              )}
            >
              {/* 상단: 이름, 타입 아이콘, 상태 배지, 토글 */}
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500 flex-shrink-0">
                      {equipmentTypeIcon[eq.type]}
                    </span>
                    <span className="text-sm font-semibold text-gray-800 truncate">
                      {eq.name}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded-full text-xs font-semibold transition-all duration-300",
                        statusInfo.color
                      )}
                    >
                      {statusInfo.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <div className="flex items-center gap-1 text-[10px] text-gray-400">
                      <MapPin className="w-2.5 h-2.5" />
                      {eq.installLocation}
                    </div>
                    {/* AMR 배터리 표시 */}
                    {eq.type === "amr" && eq.battery != null && (
                      <div className="flex items-center gap-1 text-[10px]">
                        <BatteryMedium
                          className={cn(
                            "w-3 h-3",
                            eq.battery > 50
                              ? "text-green-500"
                              : eq.battery > 20
                              ? "text-yellow-500"
                              : "text-red-500"
                          )}
                        />
                        <span
                          className={cn(
                            "font-semibold",
                            eq.battery > 50
                              ? "text-green-600"
                              : eq.battery > 20
                              ? "text-yellow-600"
                              : "text-red-600"
                          )}
                        >
                          {eq.battery}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                {/* Auto/Manual 토글 스위치 */}
                <button
                  type="button"
                  onClick={() => onToggleMode(eq.id)}
                  className={cn(
                    "relative w-14 h-7 rounded-full transition-colors flex-shrink-0 ml-2",
                    isAuto ? "bg-blue-500" : "bg-gray-300"
                  )}
                >
                  <span
                    className={cn(
                      "absolute top-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform",
                      isAuto ? "translate-x-7" : "translate-x-0.5"
                    )}
                  />
                  <span
                    className={cn(
                      "absolute text-[9px] font-bold top-1/2 -translate-y-1/2",
                      isAuto ? "left-1.5 text-white" : "right-1 text-gray-500"
                    )}
                  >
                    {isAuto ? "자동" : "수동"}
                  </span>
                </button>
              </div>

              {/* 하단: 상태 변경 버튼 그룹 */}
              <div className="flex items-center gap-1.5 mt-2">
                {validStates.map((st) => {
                  const isActive = currentStatus === st;
                  const style = statusButtonStyle[st];
                  const label = equipmentStatusMap[st].label;

                  return (
                    <button
                      key={st}
                      type="button"
                      onClick={() => onChangeStatus(eq.id, st)}
                      disabled={isActive}
                      className={cn(
                        "px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all duration-200 cursor-pointer",
                        isActive ? style.active : style.inactive,
                        isActive && "cursor-default"
                      )}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
