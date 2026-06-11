import { createFileRoute, Link } from "@tanstack/react-router";
import { Wifi, Shield, Zap, ArrowRight, Phone } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TengarakoData — Connect to fast, reliable WiFi" },
      { name: "description", content: "Pay-as-you-go hotspot internet. Connect, pick a plan, and you're online in seconds." },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col px-6 pb-10 pt-12">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary">
            <Wifi className="h-5 w-5 animate-signal" />
          </div>
          <span className="font-display text-base font-bold tracking-tight">TengarakoData</span>
        </div>
        <Link
          to="/login"
          className="text-sm font-semibold text-primary"
        >
          Sign in
        </Link>
      </header>

      <section className="mt-12 text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-signal" />
          Network online
        </span>
        <h1 className="mt-6 font-display text-4xl font-bold leading-[1.05]">
          You're one tap from <span className="gradient-text">fast WiFi</span>.
        </h1>
        <p className="mt-4 text-base text-muted-foreground">
          Connect, choose a plan, and stream, study or call without the buffering.
        </p>

        <div className="mt-8 flex flex-col gap-3">
          <Link
            to="/login"
            className="tap-target inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-[0_10px_40px_-10px_oklch(0.78_0.17_195/0.5)] transition active:scale-[0.98]"
          >
            Connect now <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            to="/login"
            className="tap-target inline-flex items-center justify-center rounded-2xl border border-border bg-surface px-6 py-3.5 text-sm font-semibold"
          >
            I have an account
          </Link>
        </div>
      </section>

      <section className="mt-12 grid grid-cols-3 gap-3">
        {[
          { icon: Zap, label: "Up to 50 Mbps" },
          { icon: Shield, label: "Secure access" },
          { icon: Phone, label: "Mobile-first" },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="surface-card flex flex-col items-center gap-2 px-2 py-4 text-center">
            <Icon className="h-5 w-5 text-primary" />
            <span className="text-[11px] font-medium text-muted-foreground">{label}</span>
          </div>
        ))}
      </section>

      <section className="surface-card mt-8 p-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">Packages from $15</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Bronze · Silver · Gold · Platinum — pick what fits your day.
        </p>
      </section>

      <footer className="mt-auto pt-10 text-center text-xs text-muted-foreground">
        Need help? Call <a href="tel:+254700000000" className="text-primary">+254 700 000 000</a>
      </footer>
    </div>
  );
}
