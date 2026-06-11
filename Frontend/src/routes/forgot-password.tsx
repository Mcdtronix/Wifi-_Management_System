import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState } from "react";
import { Loader2, ArrowLeft, ShieldCheck, EyeOff, Eye } from "lucide-react";
import { Api } from "@/lib/api";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Forgot Password — TengarakoData" },
    ],
  }),
  component: ForgotPasswordPage,
});

const step1Schema = z.object({
  username: z.string().trim().min(3, "Username is required"),
  phone_number: z.string().trim().regex(/^\+?\d[\d\s-]{7,15}$/, "Enter your full registered phone number"),
});
type Step1Values = z.infer<typeof step1Schema>;

const step2Schema = z.object({
  otp: z.string().length(6, "OTP must be exactly 6 digits"),
  new_password: z.string().min(8, "Password must be at least 8 characters"),
  confirm_password: z.string().min(8, "Password must be at least 8 characters"),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords do not match",
  path: ["confirm_password"],
});
type Step2Values = z.infer<typeof step2Schema>;

function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showPwd, setShowPwd] = useState(false);

  // Step 1 Form
  const {
    register: reg1,
    handleSubmit: submit1,
    formState: { errors: err1, isSubmitting: sub1 },
  } = useForm<Step1Values>({
    mode: "onChange",
    resolver: zodResolver(step1Schema),
    defaultValues: { username: "", phone_number: "" },
  });

  // Step 2 Form
  const {
    register: reg2,
    handleSubmit: submit2,
    formState: { errors: err2, isSubmitting: sub2 },
  } = useForm<Step2Values>({
    mode: "onChange",
    resolver: zodResolver(step2Schema),
    defaultValues: { otp: "", new_password: "", confirm_password: "" },
  });

  const onStep1 = async (v: Step1Values) => {
    setError(null);
    try {
      await Api.auth.requestPasswordReset({
        username: v.username,
        phone_number: v.phone_number,
      });
      setUsername(v.username);
      setStep(2);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to request reset.");
    }
  };

  const onStep2 = async (v: Step2Values) => {
    setError(null);
    try {
      await Api.auth.confirmPasswordReset({
        username,
        otp: v.otp,
        new_password: v.new_password,
        confirm_password: v.confirm_password,
      });
      setSuccess("Password has been reset successfully! Redirecting...");
      setTimeout(() => {
        navigate({ to: "/login" });
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to confirm reset.");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="surface-card w-full max-w-md p-8">
        
        <Link to="/login" className="mb-6 inline-flex items-center text-sm font-medium text-muted-foreground hover:text-foreground">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to login
        </Link>

        {step === 1 ? (
          <>
            <h1 className="font-display text-2xl font-bold">Reset Password</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Enter your username and registered phone number to receive a secure OTP code via SMS.
            </p>

            <form onSubmit={submit1(onStep1)} noValidate className="mt-6 flex flex-col gap-4">
              <Field label="Username" error={err1.username?.message}>
                <input
                  type="text"
                  autoCapitalize="none"
                  spellCheck={false}
                  className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
                  {...reg1("username")}
                />
              </Field>

              <Field label="Phone Number" error={err1.phone_number?.message}>
                <input
                  type="tel"
                  placeholder="+254..."
                  className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
                  {...reg1("phone_number")}
                />
              </Field>

              {error && (
                <p className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={sub1}
                className="tap-target mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3.5 font-semibold text-primary-foreground disabled:opacity-60"
              >
                {sub1 && <Loader2 className="h-5 w-5 animate-spin" />}
                Send Reset Code
              </button>
            </form>
          </>
        ) : (
          <>
            <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <h1 className="font-display text-2xl font-bold">Verify & Reset</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              We've sent a 6-digit code to your phone. Enter it below to secure your account.
            </p>

            {success ? (
              <div className="mt-6 rounded-xl border border-success/40 bg-success/10 p-4 text-center font-medium text-success">
                {success}
              </div>
            ) : (
              <form onSubmit={submit2(onStep2)} noValidate className="mt-6 flex flex-col gap-4">
                <Field label="6-Digit OTP Code" error={err2.otp?.message}>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="123456"
                    className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-center text-lg tracking-widest outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
                    {...reg2("otp")}
                  />
                </Field>

                <Field label="New Password" error={err2.new_password?.message}>
                  <div className="relative">
                    <input
                      type={showPwd ? "text" : "password"}
                      placeholder="Min 8 characters"
                      className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 pr-12 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
                      {...reg2("new_password")}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd((v) => !v)}
                      className="tap-target absolute right-1 top-1/2 -translate-y-1/2 rounded-lg px-2 text-muted-foreground hover:text-foreground"
                    >
                      {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </Field>

                <Field label="Confirm Password" error={err2.confirm_password?.message}>
                  <input
                    type={showPwd ? "text" : "password"}
                    className="tap-target w-full rounded-xl border border-border bg-surface px-4 py-3 text-base outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/30"
                    {...reg2("confirm_password")}
                  />
                </Field>

                {error && (
                  <p className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    {error}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={sub2}
                  className="tap-target mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary px-4 py-3.5 font-semibold text-primary-foreground disabled:opacity-60"
                >
                  {sub2 && <Loader2 className="h-5 w-5 animate-spin" />}
                  Confirm & Reset Password
                </button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const Field = ({ children, label, error }: { children: React.ReactNode; label: string; error?: string }) => (
  <div className="flex flex-col gap-1.5">
    <label className="text-sm font-medium">{label}</label>
    {children}
    {error && <p className="text-xs font-medium text-destructive">{error}</p>}
  </div>
);
