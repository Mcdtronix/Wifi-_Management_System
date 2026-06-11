import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Users, Ticket, Package, LogOut, Wifi, Activity, Smartphone, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Wifi;
}

const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Home", icon: LayoutDashboard },
  { to: "/admin/subscribers", label: "Users", icon: Users },
  { to: "/admin/plans", label: "Plans", icon: Package },
  { to: "/admin/vouchers", label: "Vouchers", icon: Ticket },
];

const SUB_NAV: NavItem[] = [
  { to: "/subscriber", label: "Home", icon: LayoutDashboard },
  { to: "/subscriber/usage", label: "Usage", icon: Activity },
  { to: "/subscriber/device", label: "Device", icon: Smartphone },
  { to: "/subscriber/renew", label: "Renew", icon: RefreshCw },
];

export function MobileShell({
  title,
  subtitle,
  children,
  variant,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  variant: "admin" | "subscriber";
}) {
  const nav = variant === "admin" ? ADMIN_NAV : SUB_NAV;
  const { logout } = useAuth();
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col">
      <header className="sticky top-0 z-20 border-b border-border bg-background/80 px-5 pb-4 pt-6 backdrop-blur-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-widest text-primary">
              {variant === "admin" ? "Admin Console" : "My Account"}
            </p>
            <h1 className="mt-1 truncate font-display text-2xl font-bold">{title}</h1>
            {subtitle && <p className="mt-0.5 truncate text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          <button
            onClick={logout}
            aria-label="Sign out"
            className="tap-target inline-flex shrink-0 items-center justify-center rounded-full border border-border bg-surface text-muted-foreground transition hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      <main className="flex-1 px-5 pb-28 pt-5">{children}</main>

      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-30 mx-auto max-w-md px-3 pb-4"
      >
        <div className="surface-card flex items-center justify-around gap-1 rounded-2xl border-white/10 bg-surface/90 px-2 py-2 backdrop-blur-xl">
          {nav.map((item) => {
            const active = path === item.to || (item.to !== `/${variant}` && path.startsWith(item.to));
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={[
                  "tap-target flex flex-1 flex-col items-center justify-center gap-0.5 rounded-xl px-2 py-1.5 text-[11px] font-medium transition",
                  active
                    ? "bg-primary/15 text-primary"
                    : "text-muted-foreground hover:text-foreground",
                ].join(" ")}
              >
                <Icon className="h-5 w-5" strokeWidth={active ? 2.4 : 1.8} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
