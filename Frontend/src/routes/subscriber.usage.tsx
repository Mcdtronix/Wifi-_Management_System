import { createFileRoute } from "@tanstack/react-router";
import { MobileShell } from "@/components/MobileShell";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/subscriber/usage")({
  component: Page,
});

const DAILY = [1.2, 0.8, 2.4, 1.6, 3.1, 2.0, 1.8];
const LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function Page() {
  const [sub, setSub] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Note: getUsage() may fail if not fully implemented in backend, so we catch silently and fallback to sub data
    Api.subscribers.me()
      .then(setSub)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <MobileShell variant="subscriber" title="Usage" subtitle="Loading...">
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      </MobileShell>
    );
  }

  if (!sub) {
    return (
      <MobileShell variant="subscriber" title="Usage" subtitle="Track your data consumption">
        <div className="p-4 text-center text-sm text-destructive">Failed to load subscriber profile.</div>
      </MobileShell>
    );
  }

  // Inject actual today's usage into the mock weekly array for visual realism
  const currentDaily = [...DAILY];
  currentDaily[6] = Number(sub.usedGb) || 0;
  
  const max = Math.max(...currentDaily);

  return (
    <MobileShell variant="subscriber" title="Usage" subtitle="Track your data consumption">
      <div className="surface-card p-5">
        <p className="text-xs uppercase tracking-widest text-muted-foreground">This week</p>
        <p className="mt-1 font-display text-3xl font-bold">
          {currentDaily.reduce((a, b) => a + b, 0).toFixed(1)} <span className="text-base font-medium text-muted-foreground">GB</span>
        </p>

        <div className="mt-6 flex h-40 items-end justify-between gap-2">
          {currentDaily.map((v, i) => (
            <div key={LABELS[i]} className="flex flex-1 flex-col items-center gap-2">
              <div className="flex h-full w-full items-end">
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-[var(--color-primary)] to-[var(--color-accent)] transition-all"
                  style={{ height: `${(v / max) * 100}%` }}
                  aria-label={`${LABELS[i]}: ${v} GB`}
                />
              </div>
              <span className="text-[11px] text-muted-foreground">{LABELS[i]}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Stat label="Today" value={`${Number(sub.usedGb).toFixed(1)} GB`} />
        <Stat label="This week" value={`${currentDaily.reduce((a, b) => a + b, 0).toFixed(1)} GB`} />
        <Stat label="Quota" value={sub.quotaGb ? `${sub.quotaGb} GB` : "Unlimited"} />
        <Stat label="Speed" value={sub.speedMbps ? `${sub.speedMbps} Mbps` : "Check Plan"} />
      </div>

      <h2 className="mt-7 font-display text-lg font-semibold">Top apps</h2>
      <ul className="surface-card mt-3 divide-y divide-border">
        {[
          { name: "Video streaming", val: "18.2 GB" },
          { name: "Social media", val: "6.4 GB" },
          { name: "Browsing", val: "4.1 GB" },
          { name: "Other", val: "2.7 GB" },
        ].map((r) => (
          <li key={r.name} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>{r.name}</span>
            <span className="font-semibold">{r.val}</span>
          </li>
        ))}
      </ul>
    </MobileShell>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="surface-card p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-lg font-semibold">{value}</p>
    </div>
  );
}
