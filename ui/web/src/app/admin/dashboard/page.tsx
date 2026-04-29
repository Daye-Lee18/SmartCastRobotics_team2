"use client";

/**
 * /admin/dashboard — smartcast schema 기반 운영 대시보드.
 *
 * KPI 카드 4종 + 시계열 차트 3종을 단일 화면에서 확인.
 * 데이터 출처:
 *   - /api/dashboard/stats (KPI + timescaledb_enabled)
 *   - /api/production/hourly?hours=24 (시간대별 생산 line)
 *   - /api/production/weekly?weeks=8 (주간 생산 bar)
 *   - /api/quality/trend?hours=24 (equip vs trans err_log composed)
 *
 * TimescaleDB 검출 시 "TS: ON" badge, 미검출 시 "TS: OFF (date_trunc 폴백)".
 */
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Database,
  Factory,
  Package,
  Server,
  TrendingUp,
} from "lucide-react";

// ────────────────────────────────────────
// Types (smartcast 응답 shape)
// ────────────────────────────────────────

type DashboardStatsV2 = {
  total_orders: number;
  orders_in_production: number;
  orders_completed: number;
  orders_pending: number;
  total_items: number;
  good_items: number;
  defective_items: number;
  defect_rate_pct: number;
  alerts_today: number;
  active_resources: number;
  snapshot_at: string;
  timescaledb_enabled: boolean;
};

type HourlyPoint = { bucket: string; produced: number };
type WeeklyPoint = { bucket: string; produced: number };
type TrendPoint = { bucket: string; source: "equip" | "trans"; count: number };

// ────────────────────────────────────────
// Fetchers (snake_case 그대로 사용 — adapter 우회)
// ────────────────────────────────────────

async function jsonGet<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ────────────────────────────────────────
// Helpers
// ────────────────────────────────────────

function formatHour(iso: string): string {
  // "2026-04-19T12:00:00" → "12:00"
  const t = iso.split("T")[1] ?? "";
  return t.slice(0, 5);
}

function formatDate(iso: string): string {
  return iso.split("T")[0] ?? iso;
}

function pivotTrend(points: TrendPoint[]): Array<{ bucket: string; equip: number; trans: number }> {
  const byBucket: Record<string, { equip: number; trans: number }> = {};
  for (const p of points) {
    const b = p.bucket;
    if (!byBucket[b]) byBucket[b] = { equip: 0, trans: 0 };
    byBucket[b][p.source] = p.count;
  }
  return Object.entries(byBucket)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([bucket, v]) => ({ bucket: formatHour(bucket), ...v }));
}

// ────────────────────────────────────────
// KpiCard
// ────────────────────────────────────────

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  accent,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string; // tailwind from-X to-Y
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
        </div>
        <div className={`rounded-lg p-2.5 bg-gradient-to-br ${accent} text-white shadow-sm`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────
// Main page
// ────────────────────────────────────────

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStatsV2 | null>(null);
  const [hourly, setHourly] = useState<HourlyPoint[]>([]);
  const [weekly, setWeekly] = useState<WeeklyPoint[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const [s, h, w, t] = await Promise.all([
          jsonGet<DashboardStatsV2>("/api/dashboard/stats"),
          jsonGet<HourlyPoint[]>("/api/production/hourly?hours=24"),
          jsonGet<WeeklyPoint[]>("/api/production/weekly?weeks=8"),
          jsonGet<TrendPoint[]>("/api/quality/trend?hours=24"),
        ]);
        if (!alive) return;
        setStats(s);
        setHourly(h);
        setWeekly(w);
        setTrend(t);
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    const id = setInterval(load, 10_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (loading) {
    return <div className="p-8 text-gray-500">Loading dashboard…</div>;
  }
  if (error) {
    return <div className="p-8 text-red-600">대시보드 로드 실패: {error}</div>;
  }
  if (!stats) {
    return <div className="p-8 text-gray-500">No data</div>;
  }

  const hourlyChart = hourly.map((h) => ({ time: formatHour(h.bucket), produced: h.produced }));
  const weeklyChart = weekly.map((w) => ({ week: formatDate(w.bucket), produced: w.produced }));
  const trendChart = pivotTrend(trend);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">운영 대시보드</h1>
            <p className="mt-1 text-sm text-gray-500">
              smartcast schema · 마지막 갱신 {new Date(stats.snapshot_at).toLocaleString("ko-KR")}
            </p>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${
              stats.timescaledb_enabled
                ? "bg-green-100 text-green-700 border border-green-200"
                : "bg-gray-100 text-gray-600 border border-gray-200"
            }`}
            title="TimescaleDB extension 가용 여부"
          >
            <Database className="h-3.5 w-3.5" />
            TimescaleDB: {stats.timescaledb_enabled ? "ON" : "OFF (date_trunc 폴백)"}
          </span>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KpiCard
            title="전체 발주"
            value={stats.total_orders}
            subtitle={`생산중 ${stats.orders_in_production} · 완료 ${stats.orders_completed} · 대기 ${stats.orders_pending}`}
            icon={Package}
            accent="from-blue-500 to-indigo-600"
          />
          <KpiCard
            title="전체 아이템"
            value={stats.total_items}
            subtitle={`양품 ${stats.good_items} · 불량 ${stats.defective_items}`}
            icon={Factory}
            accent="from-purple-500 to-pink-600"
          />
          <KpiCard
            title="불량률"
            value={`${stats.defect_rate_pct.toFixed(2)}%`}
            subtitle="검사 완료 기준"
            icon={CheckCircle}
            accent="from-amber-500 to-orange-600"
          />
          <KpiCard
            title="금일 알람"
            value={stats.alerts_today}
            subtitle={`활성 자원 ${stats.active_resources} 대`}
            icon={AlertTriangle}
            accent="from-red-500 to-rose-600"
          />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-600" />
                시간대별 생산 (24h)
              </h2>
              <span className="text-xs text-gray-400">
                /api/production/hourly · {hourlyChart.length} buckets
              </span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={hourlyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="produced" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <Activity className="h-4 w-4 text-purple-600" />
                주간 생산 (8주)
              </h2>
              <span className="text-xs text-gray-400">
                /api/production/weekly · {weeklyChart.length} weeks
              </span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={weeklyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="week" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="produced" fill="#9333ea" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <Server className="h-4 w-4 text-rose-600" />
                err_log 트렌드 (24h)
              </h2>
              <span className="text-xs text-gray-400">
                /api/quality/trend · {trendChart.length} buckets
              </span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trendChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="bucket" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="equip" stackId="err" fill="#dc2626" name="equip_err_log" />
                <Bar dataKey="trans" stackId="err" fill="#f97316" name="trans_err_log" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <p className="mt-6 text-xs text-gray-400">
          10초마다 자동 갱신. 시계열 차트는 backend 가 TimescaleDB extension 검출 시 hypertable 쿼리,
          미검출 시 date_trunc 폴백을 사용합니다.
        </p>
      </div>
    </div>
  );
}
