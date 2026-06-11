import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Check, Loader2, Zap } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/apiClient";

export const Route = createFileRoute("/subscriber/renew")({
  component: Page,
});

function Page() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string>("");
  const [paying, setPaying] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    Api.plans.list()
      .then((data) => {
        setPlans(data);
        if (data.length > 0) setSelected(data[0].id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const pay = async () => {
    setPaying(true);
    // In a real flow, this invokes M-Pesa STK push via your backend,
    // and polls for completion or uses websockets.
    try {
      // Mocking the wait
      await new Promise((r) => setTimeout(r, 900));
      // Hypothetical renew call: await fetchApi("/api/v1/subscriptions/renew/", { method: "POST" })
      setDone(true);
      setTimeout(() => navigate({ to: "/subscriber" }), 900);
    } finally {
      setPaying(false);
    }
  };

  return (
    <MobileShell variant="subscriber" title="Renew subscription" subtitle="Pick a plan that fits your needs">
      {loading ? (
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      ) : (
        <div className="flex flex-col gap-3">
          {plans.map((p) => {
            const active = selected === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelected(p.id)}
              className={[
                "surface-card relative flex items-center justify-between gap-3 p-4 text-left transition",
                active ? "border-primary ring-2 ring-primary/40" : "hover:border-white/20",
              ].join(" ")}
            >
              {p.popular && (
                <span className="absolute -top-2 right-4 rounded-full bg-accent px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent-foreground">
                  Popular
                </span>
              )}
              <div className="min-w-0">
                <p className="font-display text-lg font-bold">{p.name}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {p.bandwidthMbps} Mbps · {p.quotaGb ? `${p.quotaGb} GB` : "Unlimited"} · {p.durationDays} days
                </p>
              </div>
              <div className="text-right">
                <p className="font-display text-base font-bold">${Number(p.price).toLocaleString()}</p>
                <div
                  className={[
                    "mt-1 grid h-6 w-6 place-items-center rounded-full border transition",
                    active ? "border-primary bg-primary text-primary-foreground" : "border-border",
                  ].join(" ")}
                >
                  {active && <Check className="h-4 w-4" />}
                </div>
              </div>
            </button>
          );
          })}
        </div>
      )}

      <div className="surface-card mt-6 p-4">
        <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-primary">
          <Zap className="h-3.5 w-3.5" /> Payment
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          You'll be charged via M-Pesa to <span className="font-semibold text-foreground">+254 712 345 678</span>.
        </p>

        <button
          onClick={pay}
          disabled={paying || done || loading}
          className="tap-target mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          {paying && <Loader2 className="h-4 w-4 animate-spin" />}
          {done ? "Payment received" : paying ? "Processing…" : `Pay & activate ${plans.find(p => p.id === selected)?.name || ''}`}
        </button>
      </div>
    </MobileShell>
  );
}
