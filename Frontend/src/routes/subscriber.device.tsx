import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Smartphone, CheckCircle2, Loader2 } from "lucide-react";
import { MobileShell } from "@/components/MobileShell";
import { Api } from "@/lib/api";
import { useEffect } from "react";

export const Route = createFileRoute("/subscriber/device")({
  component: Page,
});

const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$/;

const schema = z.object({
  deviceName: z.string().trim().min(2, "Enter a device name").max(64, "Too long"),
  mac: z.string().trim().regex(macRegex, "Use format AA:BB:CC:DD:EE:FF"),
  reason: z.string().trim().min(10, "Please share at least 10 characters").max(280, "Keep it under 280 chars"),
});

type FormValues = z.infer<typeof schema>;

function Page() {
  const [sub, setSub] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    Api.subscribers.me()
      .then(setSub)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { deviceName: "", mac: "", reason: "" },
  });

  const onSubmit = async (_values: FormValues) => {
    await new Promise((r) => setTimeout(r, 700));
    setSubmitted(true);
    reset();
  };

  if (loading) {
    return (
      <MobileShell variant="subscriber" title="My device" subtitle="Loading...">
        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-primary" /></div>
      </MobileShell>
    );
  }

  if (!sub) {
    return (
      <MobileShell variant="subscriber" title="My device" subtitle="Manage your registered device">
        <div className="p-4 text-center text-sm text-destructive">Failed to load subscriber profile.</div>
      </MobileShell>
    );
  }

  return (
    <MobileShell variant="subscriber" title="My device" subtitle="Manage your registered device">
      <div className="surface-card flex items-center gap-3 p-4">
        <div className="grid h-12 w-12 place-items-center rounded-xl bg-primary/15 text-primary">
          <Smartphone className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <p className="font-display text-base font-semibold">{sub.deviceName}</p>
          <p className="truncate text-xs text-muted-foreground">Registered · MAC {sub.macAddress}</p>
        </div>
      </div>

      <h2 className="mt-7 font-display text-lg font-semibold">Request device change</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        An admin will review and approve your request, usually within 24 hours.
      </p>

      {submitted && (
        <div className="surface-card mt-4 flex items-start gap-3 border-success/40 bg-success/10 p-4 text-sm">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-success" />
          <div>
            <p className="font-semibold text-success">Request submitted</p>
            <p className="text-muted-foreground">We'll notify you on WhatsApp once approved.</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-5 flex flex-col gap-4">
        <Field label="New device name" error={errors.deviceName?.message}>
          <input
            placeholder="e.g. iPhone 15"
            aria-invalid={!!errors.deviceName}
            className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
            {...register("deviceName")}
          />
        </Field>

        <Field label="MAC address" error={errors.mac?.message}>
          <input
            placeholder="AA:BB:CC:DD:EE:FF"
            autoCapitalize="characters"
            spellCheck={false}
            inputMode="text"
            aria-invalid={!!errors.mac}
            className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 font-mono text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
            {...register("mac")}
          />
        </Field>

        <Field label="Reason" error={errors.reason?.message}>
          <textarea
            rows={3}
            placeholder="My old phone broke and I bought a new one…"
            aria-invalid={!!errors.reason}
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/30"
            {...register("reason")}
          />
        </Field>

        <button
          type="submit"
          disabled={isSubmitting}
          className="tap-target mt-1 inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground disabled:opacity-60"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Submit request
        </button>
      </form>
    </MobileShell>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p role="alert" className="text-xs font-medium text-destructive">{error}</p>}
    </div>
  );
}
