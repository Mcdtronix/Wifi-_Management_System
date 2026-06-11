import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Eye, EyeOff, Loader2, Wifi } from "lucide-react";
import { useAuth, type Role } from "@/lib/auth";
import { fetchApi } from "@/lib/apiClient";
import { Api } from "@/lib/api";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — TengarakoData" },
      { name: "description", content: "Sign in to your TengarakoData hotspot account." },
    ],
  }),
  component: LoginPage,
});

const schema = z.object({
  username: z
    .string()
    .trim()
    .min(3, "Username must be at least 3 characters")
    .max(64, "Username is too long")
    .regex(/^[a-zA-Z0-9._@-]+$/, "Use letters, numbers, '@', '.', '_' or '-'"),
  password: z
    .string()
    .min(6, "Password must be at least 6 characters")
    .max(128, "Password is too long"),
  remember: z.boolean().optional(),
});

type FormValues = z.infer<typeof schema>;

function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    mode: "onChange",
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "", remember: true },
  });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      console.log("[DEBUG] Starting Login Flow...");
      
      const role: Role = values.username.toLowerCase().startsWith("admin") ? "admin" : "subscriber";
      let data;
      
      const urlParams = new URLSearchParams(window.location.search);
      const macAddress = urlParams.get("clientMac") || urlParams.get("mac") || "";
      
      const getDeviceName = () => {
        const ua = navigator.userAgent;
        if (/android/i.test(ua)) return "Android Device";
        if (/iPad|iPhone|iPod/.test(ua)) return "iOS Device";
        if (/windows/i.test(ua)) return "Windows PC";
        if (/mac/i.test(ua)) return "Mac";
        if (/linux/i.test(ua)) return "Linux PC";
        return "Unknown Device";
      };
      
      if (role === "admin") {
        data = await Api.auth.adminLogin({
          email: values.username,
          password: values.password,
        });
      } else {
        data = await Api.auth.subscriberLogin({
          username: values.username,
          password: values.password,
          mac_address: macAddress,
          device_name: getDeviceName(),
        });
      }
      
      login({ username: values.username, role }, { access: data.access, refresh: data.refresh });
      navigate({ to: role === "admin" ? "/admin" : "/subscriber" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    }
  };

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col px-6 pb-10 pt-10">
      <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary">
          <Wifi className="h-5 w-5" />
        </div>
        <span className="font-display font-semibold text-foreground">TengarakoData</span>
      </Link>

      <div className="mt-10">
        <h1 className="font-display text-3xl font-bold">Welcome back</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Sign in to manage your subscription, devices and usage.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-8 flex flex-col gap-4">
        <Field label="Username" error={errors.username?.message}>
          <input
            type="text"
            autoComplete="username"
            inputMode="text"
            autoCapitalize="none"
            spellCheck={false}
            placeholder="e.g. jmwangi"
            aria-invalid={!!errors.username}
            className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
            {...register("username")}
          />
        </Field>

        <Field label="Password" error={errors.password?.message}>
          <div className="relative">
            <input
              type={showPwd ? "text" : "password"}
              autoComplete="current-password"
              placeholder="••••••••"
              aria-invalid={!!errors.password}
              className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 pr-12 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPwd((v) => !v)}
              aria-label={showPwd ? "Hide password" : "Show password"}
              className="tap-target absolute right-1 top-1/2 -translate-y-1/2 rounded-lg px-2 text-muted-foreground hover:text-foreground"
            >
              {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </Field>

        <div className="flex items-center justify-between text-sm">
          <label className="inline-flex items-center gap-2 text-muted-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border bg-surface accent-[var(--color-primary)]"
              {...register("remember")}
            />
            Remember me
          </label>
          <Link to="/forgot-password" className="font-medium text-primary">
            Forgot password?
          </Link>
        </div>

        {error && (
          <p role="alert" className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="tap-target mt-2 inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-[0_10px_40px_-10px_oklch(0.78_0.17_195/0.5)] transition active:scale-[0.98] disabled:opacity-60"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="mt-2 text-center text-xs text-muted-foreground">
          Tip: username starting with <span className="font-semibold text-foreground">admin</span> opens the admin console.
        </p>
      </form>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-foreground">{label}</label>
      {children}
      {error && (
        <p role="alert" className="text-xs font-medium text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
