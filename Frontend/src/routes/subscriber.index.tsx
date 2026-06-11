import { createFileRoute, Link } from "@tanstack/react-router";
import { Activity, Calendar, Smartphone, Wifi, ArrowRight } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { useAuth } from "@/lib/auth";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/subscriber/")({
  component: Page,
});

function Page() {
  const { session } = useAuth();
  const [sub, setSub] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Api.subscribers.me()
      .then(setSub)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <MobileShell variant="subscriber" title="Loading..." subtitle="Please wait">
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      </MobileShell>
    );
  }

  if (!sub) {
    return (
      <MobileShell variant="subscriber" title="Error" subtitle="Profile not found">
        <div className="p-4 text-center text-sm text-destructive">Failed to load subscriber profile.</div>
      </MobileShell>
    );
  }

  const pct = sub.quotaGb ? Math.min(100, (sub.usedGb / sub.quotaGb) * 100) : 0;
  const remaining = sub.quotaGb ? Math.max(0, sub.quotaGb - sub.usedGb) : null;

  // Attempt to parse bandwidth if plan has "Mbps" string or default to generic logic
  // Since backend doesn't explicitly return speed in summary, we'll placeholder it for now
  const speed = "10 Mbps"; 

  return (
    <MobileShell
      variant="subscriber"
      title={`Hi, ${session?.username ?? sub.fullName?.split(" ")[0]}`}
      subtitle={`${sub.plan} plan · expires ${sub.expiresAt}`}
    >
      <div className="surface-card relative overflow-hidden p-5">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-primary/20 blur-3xl"
        />
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-signal" />
          Connected
        </div>
        <div className="mt-4 flex items-end justify-between">
          <div>
            <p className="text-xs text-muted-foreground">Data used</p>
            <p className="font-display text-3xl font-bold">
              {Number(sub.usedGb).toFixed(1)} <span className="text-base font-medium text-muted-foreground">GB</span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Remaining</p>
            <p className="font-display text-xl font-semibold">
              {remaining === null ? "∞" : `${remaining.toFixed(1)} GB`}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-accent)] transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-muted-foreground">
            <span>0 GB</span>
            <span>{sub.quotaGb ? `${sub.quotaGb} GB` : "Unlimited"}</span>
          </div>
        </div>

        <Link
          to="/subscriber/renew"
          className="tap-target mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground"
        >
          Renew plan <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <InfoTile icon={Calendar} label="Expires" value={sub.expiresAt ?? "N/A"} />
        <InfoTile icon={Wifi} label="Speed" value={speed} />
        <InfoTile icon={Smartphone} label="Device" value={sub.deviceName} />
        <InfoTile icon={Activity} label="Status" value={sub.status} tone={sub.status === "active" ? "success" : undefined} />
      </div>

      <h2 className="mt-7 font-display text-lg font-semibold">Recent activity</h2>
      <ul className="surface-card mt-3 divide-y divide-border">
        <li className="p-4 text-center text-sm text-muted-foreground">
          Activity log loading...
        </li>
      </ul>
    </MobileShell>
  );
}

function InfoTile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  tone?: "success";
}) {
  return (
    <div className="surface-card p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className={`mt-1.5 truncate font-display text-base font-semibold ${tone === "success" ? "text-success" : ""}`}>
        {value}
      </p>
    </div>
  );
}
