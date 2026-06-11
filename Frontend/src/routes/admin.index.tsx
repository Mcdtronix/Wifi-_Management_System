import { createFileRoute, Link } from "@tanstack/react-router";
import { Users, UserCheck, Wifi, DollarSign, AlertTriangle, ShieldAlert, Smartphone, ArrowRight } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { StatCard } from "@/components/StatCard";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/admin/")({
  component: Page,
});

function Page() {
  const [s, setS] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Api.dashboard.getStats()
      .then(setS)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <MobileShell variant="admin" title="Dashboard" subtitle="Realtime network overview">
      {loading ? (
        <div className="flex justify-center p-10"><AlertTriangle className="animate-spin text-primary" /></div>
      ) : s ? (
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Active" value={s.activeSubscribers.toLocaleString()} icon={UserCheck} tone="success" />
          <StatCard label="Online now" value={s.onlineUsers.toLocaleString()} icon={Wifi} tone="primary" />
          <StatCard label="Today" value={`$${(s.revenueToday / 1000).toFixed(1)}k`} icon={DollarSign} hint="Revenue" />
          <StatCard label="This month" value={`$${(s.revenueMonth / 1000000).toFixed(2)}M`} icon={DollarSign} hint="Revenue" />
          <StatCard label="Expired" value={s.expiredSubscribers} icon={Users} tone="warning" />
          <StatCard label="Device reqs" value={s.pendingDeviceRequests} icon={Smartphone} tone="warning" />
          <StatCard label="Quota alerts" value={s.quotaViolations} icon={AlertTriangle} tone="warning" />
          <StatCard label="Fraud" value={s.fraudAlerts} icon={ShieldAlert} tone="destructive" />
        </div>
      ) : (
        <div className="p-4 text-center text-sm text-destructive">Failed to load stats.</div>
      )}

      <h2 className="mt-7 font-display text-lg font-semibold">Quick actions</h2>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <QuickLink to="/admin/subscribers" label="Manage subscribers" />
        <QuickLink to="/admin/plans" label="Plans & pricing" />
        <QuickLink to="/admin/vouchers" label="Vouchers" />
        <QuickLink to="/admin" label="Network health" />
      </div>

      <h2 className="mt-7 font-display text-lg font-semibold">Recent activity</h2>
      <ul className="surface-card mt-3 divide-y divide-border">
        {[
          { t: "2 min ago", e: "New subscriber: Aisha Hassan (Gold)" },
          { t: "14 min ago", e: "Device change approved — Brian Otieno" },
          { t: "1 hr ago", e: "Fraud alert: multiple devices for user sam.k" },
          { t: "3 hrs ago", e: "Voucher batch generated — 50 × Silver" },
        ].map((r) => (
          <li key={r.t} className="flex items-start justify-between gap-3 px-4 py-3">
            <span className="text-sm">{r.e}</span>
            <span className="shrink-0 text-xs text-muted-foreground">{r.t}</span>
          </li>
        ))}
      </ul>
    </MobileShell>
  );
}

function QuickLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="surface-card tap-target flex items-center justify-between gap-2 p-4 text-sm font-medium transition hover:border-primary/40"
    >
      <span>{label}</span>
      <ArrowRight className="h-4 w-4 text-primary" />
    </Link>
  );
}
