import { useId, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const CHART = {
  teal: "#0f766e",
  sky: "#0284c7",
  violet: "#7c3aed",
  amber: "#d97706",
  orange: "#ea580c",
  rose: "#e11d48",
  slate: "#64748b",
  grid: "#e2e8f0",
  axis: "#94a3b8",
};

const SEVERITY_FILL: Record<string, string> = {
  critical: CHART.rose,
  high: CHART.orange,
  medium: CHART.amber,
  low: CHART.teal,
};

const RISK_FILL: Record<string, string> = {
  critical: CHART.rose,
  high: CHART.orange,
  medium: CHART.amber,
  low: CHART.teal,
  unknown: CHART.slate,
};

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  boxShadow: "none",
  background: "rgba(255,255,255,0.96)",
  fontSize: 12,
};

export function ChartCard({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <article className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className="mb-4">
        <h2 className="text-sm font-semibold tracking-tight text-slate-800">{title}</h2>
        {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
      </div>
      {children}
    </article>
  );
}

export function EmptyChart({ label = "No data yet" }: { label?: string }) {
  return (
    <div className="flex h-[260px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 text-sm text-slate-500">
      {label}
    </div>
  );
}

type Point = Record<string, string | number>;

export function AnimatedAreaChart({
  data,
  xKey,
  yKey,
  color,
  label,
}: {
  data: Point[];
  xKey: string;
  yKey: string;
  color: string;
  label: string;
}) {
  const gradientId = useId().replace(/:/g, "");
  if (!data.length) return <EmptyChart />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.32} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={CHART.grid} strokeDasharray="4 8" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: "#0f172a" }} />
        <Area
          type="monotone"
          dataKey={yKey}
          name={label}
          stroke={color}
          strokeWidth={2.4}
          fill={`url(#${gradientId})`}
          dot={data.length < 2 ? { r: 4, fill: color, strokeWidth: 0 } : false}
          activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
          animationDuration={1100}
          animationEasing="ease-out"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function AnimatedBarChart({
  data,
  xKey,
  yKey,
  color,
  colorBy,
}: {
  data: Point[];
  xKey: string;
  yKey: string;
  color: string;
  colorBy?: Record<string, string>;
}) {
  if (!data.length) return <EmptyChart />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={CHART.grid} strokeDasharray="4 8" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(15, 23, 42, 0.04)" }} />
        <Bar
          dataKey={yKey}
          radius={[10, 10, 4, 4]}
          maxBarSize={42}
          animationDuration={900}
          animationEasing="ease-out"
        >
          {data.map((entry, index) => {
            const key = String(entry[xKey] ?? index);
            return <Cell key={key} fill={colorBy?.[key] ?? color} />;
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AnimatedDonutChart({
  data,
  nameKey,
  valueKey,
}: {
  data: Array<Record<string, string | number>>;
  nameKey: string;
  valueKey: string;
}) {
  if (!data.length) return <EmptyChart />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          innerRadius={58}
          outerRadius={92}
          paddingAngle={3}
          cornerRadius={6}
          animationDuration={1000}
          animationBegin={120}
        >
          {data.map((entry, index) => {
            const name = String(entry[nameKey] ?? index);
            return <Cell key={name} fill={RISK_FILL[name] ?? Object.values(CHART)[index % 6]} stroke="#fff" strokeWidth={2} />;
          })}
        </Pie>
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: "#475569" }} />
        <Tooltip contentStyle={tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function severityFill(name: string): string {
  return SEVERITY_FILL[name] ?? CHART.slate;
}

export function DualAreaChart({
  data,
  xKey,
  series,
}: {
  data: Point[];
  xKey: string;
  series: Array<{ key: string; color: string; label: string }>;
}) {
  const prefix = useId().replace(/:/g, "");
  if (!data.length) return <EmptyChart />;
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          {series.map((item) => (
            <linearGradient key={item.key} id={`${prefix}-${item.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={item.color} stopOpacity={0.28} />
              <stop offset="100%" stopColor={item.color} stopOpacity={0.02} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke={CHART.grid} strokeDasharray="4 8" vertical={false} />
        <XAxis dataKey={xKey} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: "#475569" }} />
        {series.map((item, index) => (
          <Area
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.label}
            stroke={item.color}
            strokeWidth={2.2}
            fill={`url(#${prefix}-${item.key})`}
            dot={data.length < 2 ? { r: 4, fill: item.color, strokeWidth: 0 } : false}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "#fff" }}
            animationDuration={1100}
            animationBegin={index * 120}
            animationEasing="ease-out"
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
