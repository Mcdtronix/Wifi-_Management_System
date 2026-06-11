import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Search, Plus, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MobileShell } from "@/components/MobileShell";
import { type Subscriber } from "@/lib/mock-data";
import { fetchApi } from "@/lib/apiClient";
import { Api } from "@/lib/api";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/admin/subscribers")({
  component: Page,
});

type Filter = "all" | "active" | "expired" | "suspended";

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "expired", label: "Expired" },
  { key: "suspended", label: "Suspended" },
];

const STATUS_TONE: Record<Subscriber["status"], string> = {
  active: "bg-success/15 text-success",
  expired: "bg-warning/15 text-warning",
  suspended: "bg-destructive/15 text-destructive",
};

function Page() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [list, setList] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [assignSubscriber, setAssignSubscriber] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([Api.subscribers.list(), Api.plans.list()])
      .then(([subsData, plansData]) => {
        setList(subsData);
        setPlans(plansData);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return list.filter((s) => {
      if (filter !== "all" && s.status !== filter) return false;
      if (!needle) return true;
      return [s.fullName, s.username, s.phone].some((v) => v.toLowerCase().includes(needle));
    });
  }, [list, q, filter]);

  return (
    <MobileShell variant="admin" title="Subscribers" subtitle={`${list.length} total`}>
      {loading ? (
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      ) : (
        <>
          <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, username, phone"
          className="tap-target w-full rounded-xl border border-border bg-surface pl-10 pr-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
        />
      </div>

      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={[
              "shrink-0 rounded-full border px-4 py-1.5 text-xs font-semibold transition",
              filter === f.key
                ? "border-primary bg-primary/15 text-primary"
                : "border-border bg-surface text-muted-foreground",
            ].join(" ")}
          >
            {f.label}
          </button>
        ))}
      </div>

      <ul className="mt-4 flex flex-col gap-3">
        {filtered.map((s) => (
          <li key={s.id} className="surface-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-display text-base font-semibold">{s.fullName}</p>
                <p className="truncate text-xs text-muted-foreground">@{s.username} · {s.phone}</p>
                <p className="truncate text-[11px] text-muted-foreground mt-1">
                  Device: {s.deviceName} ({s.macAddress})
                </p>
              </div>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_TONE[s.status]}`}>
                {s.status}
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{s.plan} · expires {s.expiresAt}</span>
              <div className="flex items-center gap-3">
                <span className="font-semibold">
                  {s.usedGb.toFixed(1)} / {s.quotaGb ?? "∞"} GB
                </span>
                <button 
                  onClick={() => setAssignSubscriber(s)}
                  className="rounded-lg bg-primary/10 px-3 py-1.5 font-semibold text-primary transition active:bg-primary/20"
                >
                  Assign Plan
                </button>
              </div>
            </div>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="surface-card p-6 text-center text-sm text-muted-foreground">
            No subscribers match your search.
          </li>
        )}
      </ul>
        </>
      )}

      <button
        onClick={() => setShowCreate(true)}
        aria-label="Create subscriber"
        className="fixed bottom-24 right-4 z-30 grid h-14 w-14 place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_10px_40px_-10px_oklch(0.78_0.17_195/0.6)] active:scale-95"
      >
        <Plus className="h-6 w-6" />
      </button>

      {showCreate && (
        <CreateSubscriberSheet
          onClose={() => setShowCreate(false)}
          onCreate={(s) => {
            setList((prev) => [s, ...prev]);
            setShowCreate(false);
          }}
        />
      )}

      {assignSubscriber && (
        <AssignPlanSheet
          subscriber={assignSubscriber}
          plans={plans}
          onClose={() => setAssignSubscriber(null)}
          onAssign={(updated) => {
            setList(list.map(s => s.id === updated.id ? { ...s, ...updated } : s));
            setAssignSubscriber(null);
          }}
        />
      )}
    </MobileShell>
  );
}

const createSchema = z.object({
  fullName: z.string().trim().min(2, "Full name is required").max(80, "Too long"),
  phone: z.string().trim().regex(/^\+?\d[\d\s-]{7,15}$/, "Enter a valid phone number"),
  username: z
    .string()
    .trim()
    .min(3, "Min 3 characters")
    .max(32, "Too long")
    .regex(/^[a-zA-Z0-9._\-@]+$/, "Letters, numbers, '.', '_', '-', or '@' only"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type CreateValues = z.infer<typeof createSchema>;

function CreateSubscriberSheet({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (s: Subscriber | any) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    mode: "onChange",
    resolver: zodResolver(createSchema),
    defaultValues: { fullName: "", phone: "", username: "", password: "" },
  });

  const onSubmit = async (v: CreateValues) => {
    try {
      const subRes = await fetchApi("/api/v1/subscribers/", {
        method: "POST",
        body: JSON.stringify({
          full_name: v.fullName,
          phone_number: v.phone,
          username: v.username,
          password: v.password,
        }),
      });

      if (!subRes.ok) {
        const errorData = await subRes.json();
        throw new Error(JSON.stringify(errorData) || "Failed to create subscriber");
      }
      
      const subscriber = await subRes.json();

      onCreate({
        id: subscriber.id,
        fullName: subscriber.full_name,
        username: subscriber.username,
        phone: subscriber.phone_number,
        plan: "No Active Plan",
        status: "active",
        expiresAt: "Pending",
        device: "Pending registration",
        usedGb: 0,
        quotaGb: null,
      });

    } catch (error) {
      console.error(error);
      alert(error instanceof Error ? error.message : "An unexpected error occurred");
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="surface-card mx-auto w-full max-w-md rounded-b-none rounded-t-2xl border-b-0 p-5"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Create subscriber"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold">New subscriber</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="tap-target grid h-9 w-9 place-items-center rounded-full border border-border"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-4 flex flex-col gap-3">
          <Input label="Full name" error={errors.fullName?.message} {...register("fullName")} />
          <Input label="Phone" type="tel" inputMode="tel" placeholder="+254 7…" error={errors.phone?.message} {...register("phone")} />
          <Input label="Username" autoCapitalize="none" spellCheck={false} error={errors.username?.message} {...register("username")} />
          <Input label="RADIUS Password" type="password" placeholder="Min 8 characters" error={errors.password?.message} {...register("password")} />

          <button
            type="submit"
            disabled={isSubmitting}
            className="tap-target mt-2 inline-flex items-center justify-center rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            {isSubmitting ? "Creating…" : "Create subscriber"}
          </button>
        </form>
      </div>
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

const assignSchema = z.object({
  planId: z.string().min(1, "Plan selection is required"),
});
type AssignValues = z.infer<typeof assignSchema>;

function AssignPlanSheet({
  subscriber,
  plans,
  onClose,
  onAssign,
}: {
  subscriber: any;
  plans: any[];
  onClose: () => void;
  onAssign: (s: any) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<AssignValues>({
    mode: "onChange",
    resolver: zodResolver(assignSchema),
    defaultValues: { planId: plans[0]?.id || "" },
  });

  const onSubmit = async (v: AssignValues) => {
    try {
      const assignRes = await fetchApi("/api/v1/subscriptions/", {
        method: "POST",
        body: JSON.stringify({
          subscriber: subscriber.id,
          plan: v.planId,
        }),
      });

      if (!assignRes.ok) {
        const errorData = await assignRes.json();
        throw new Error(JSON.stringify(errorData) || "Failed to assign the subscription plan.");
      }

      onAssign({
        id: subscriber.id,
        plan: plans.find((p) => p.id === v.planId)?.name || "Active Plan",
        expiresAt: "Pending",
      });

    } catch (error) {
      console.error(error);
      alert(error instanceof Error ? error.message : "An unexpected error occurred");
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="surface-card mx-auto w-full max-w-md rounded-b-none rounded-t-2xl border-b-0 p-5"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label="Assign plan"
      >
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold">Assign Plan</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="tap-target grid h-9 w-9 place-items-center rounded-full border border-border"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Assigning plan to <strong>{subscriber.fullName}</strong>
        </p>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Select Plan</label>
            <select
              {...register("planId")}
              className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — ${Number(p.price).toLocaleString()}
                </option>
              ))}
            </select>
            {errors.planId && (
              <p role="alert" className="text-xs font-medium text-destructive">
                {errors.planId.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="tap-target mt-2 inline-flex items-center justify-center rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
          >
            {isSubmitting ? "Assigning…" : "Assign Plan"}
          </button>
        </form>
      </div>
    </div>
  );
}
