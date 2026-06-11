import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Copy, Check, Ticket, Loader2 } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { Api } from "@/lib/api";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/admin/vouchers")({
  component: Page,
});

const STATUS_TONE: Record<string, string> = {
  unused: "bg-primary/15 text-primary",
  used: "bg-muted text-muted-foreground",
  expired: "bg-destructive/15 text-destructive",
};

const schema = z.object({
  quantity: z
    .number({ error: "Enter a number" })
    .int("Whole numbers only")
    .min(1, "At least 1")
    .max(500, "Max 500 at a time"),
  plan: z.enum(["Bronze", "Silver", "Gold", "Platinum"]),
  prefix: z
    .string()
    .trim()
    .min(2, "Min 2 chars")
    .max(6, "Max 6 chars")
    .regex(/^[A-Z0-9]+$/, "Uppercase letters & digits only"),
});
type V = z.infer<typeof schema>;

function Page() {
  const [list, setList] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [copied, setCopied] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([Api.vouchers.list(), Api.plans.list()])
      .then(([vouchersData, plansData]) => {
        setList(vouchersData);
        setPlans(plansData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<V>({
    resolver: zodResolver(schema),
    defaultValues: { quantity: 10, plan: "Silver", prefix: "TGD" },
  });

  const onGenerate = async (v: V) => {
    // In a real implementation, this would call Api.vouchers.createBatch(v)
    await new Promise((r) => setTimeout(r, 500));
    const today = new Date().toISOString().slice(0, 10);
    const created: any[] = Array.from({ length: v.quantity }, (_, i) => ({
      id: `v-${Date.now()}-${i}`,
      code: `${v.prefix}-${rand(4)}-${rand(4)}`,
      plan: v.plan,
      status: "unused",
      createdAt: today,
    }));
    setList((prev) => [...created, ...prev]);
  };

  const copy = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(code);
      setTimeout(() => setCopied(null), 1200);
    } catch {
      // ignore
    }
  };

  const stats = {
    total: list.length,
    unused: list.filter((v) => v.status === "unused").length,
    used: list.filter((v) => v.status === "used").length,
  };

  return (
    <MobileShell variant="admin" title="Vouchers" subtitle="Generate & track">
      <div className="grid grid-cols-3 gap-3">
        <Mini label="Total" value={stats.total} />
        <Mini label="Unused" value={stats.unused} tone="text-primary" />
        <Mini label="Used" value={stats.used} tone="text-muted-foreground" />
      </div>

      <div className="surface-card mt-5 p-5">
        <h2 className="font-display text-base font-semibold">Generate batch</h2>
        <form onSubmit={handleSubmit(onGenerate)} noValidate className="mt-4 flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Quantity" type="number" inputMode="numeric" error={errors.quantity?.message} {...register("quantity", { valueAsNumber: true })} />
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Plan</label>
              <select
                {...register("plan")}
                className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.name}>{p.name}</option>
                ))}
              </select>
            </div>
          </div>
          <Input label="Prefix" autoCapitalize="characters" spellCheck={false} error={errors.prefix?.message} {...register("prefix")} />
          <button
            type="submit"
            disabled={isSubmitting}
            className="tap-target mt-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            <Ticket className="h-4 w-4" /> Generate
          </button>
        </form>
      </div>

      <h2 className="mt-7 font-display text-lg font-semibold">Recent vouchers</h2>
      <ul className="mt-3 flex flex-col gap-2">
        {list.slice(0, 30).map((v) => (
          <li key={v.id} className="surface-card flex items-center justify-between gap-3 p-3">
            <div className="min-w-0">
              <p className="truncate font-mono text-sm font-semibold">{v.code}</p>
              <p className="text-[11px] text-muted-foreground">{v.plan} · {v.createdAt}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_TONE[v.status]}`}>{v.status}</span>
              <button
                onClick={() => copy(v.code)}
                aria-label={`Copy ${v.code}`}
                className="tap-target grid h-9 w-9 place-items-center rounded-full border border-border"
              >
                {copied === v.code ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </MobileShell>
  );
}

function Mini({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="surface-card p-3 text-center">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 font-display text-xl font-bold ${tone ?? ""}`}>{value}</p>
    </div>
  );
}

const Input = ({
  label,
  error,
  ...rest
}: { label: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) => (
  <div className="flex flex-col gap-1.5">
    <label className="text-sm font-medium">{label}</label>
    <input
      {...rest}
      aria-invalid={!!error}
      className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
    />
    {error && <p role="alert" className="text-xs font-medium text-destructive">{error}</p>}
  </div>
);

function rand(n: number) {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = "";
  for (let i = 0; i < n; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}
