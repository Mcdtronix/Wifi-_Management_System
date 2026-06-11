import { createFileRoute } from "@tanstack/react-router";
import { Check, Edit3 } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/admin/plans")({
  component: Page,
});

function Page() {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Api.plans.list()
      .then(setPlans)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <MobileShell variant="admin" title="Plans" subtitle="Manage pricing & quotas">
      {loading ? (
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      ) : (
        <ul className="flex flex-col gap-3">
          {plans.map((p: any) => (
            <li key={p.id} className="surface-card relative p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-display text-xl font-bold">{p.name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{p.durationDays} day cycle</p>
                </div>
                <button
                  aria-label={`Edit ${p.name} plan`}
                  className="tap-target grid h-9 w-9 place-items-center rounded-full border border-border text-muted-foreground"
                >
                  <Edit3 className="h-4 w-4" />
                </button>
              </div>

              <p className="mt-3 font-display text-3xl font-bold gradient-text">
                ${Number(p.price).toLocaleString()}
              </p>

              <ul className="mt-4 flex flex-col gap-2 text-sm">
                <Feat>{p.bandwidthMbps} Mbps download & upload</Feat>
                <Feat>{p.quotaGb ? `${p.quotaGb} GB daily data` : "Unlimited data"}</Feat>
                <Feat>1 registered device</Feat>
                <Feat>24/7 support</Feat>
              </ul>
            </li>
          ))}
        </ul>
      )}
    </MobileShell>
  );
}

function Feat({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-2">
      <Check className="h-4 w-4 text-success" />
      <span>{children}</span>
    </li>
  );
}
