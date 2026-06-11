import type { LucideIcon } from "lucide-react";

interface Props {
  label: string;
  value: string | number;
  hint?: string;
  icon?: LucideIcon;
  tone?: "default" | "primary" | "success" | "warning" | "destructive";
}

const TONE: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-foreground",
  primary: "text-primary",
  success: "text-success",
  warning: "text-warning",
  destructive: "text-destructive",
};

export function StatCard({ label, value, hint, icon: Icon, tone = "default" }: Props) {
  return (
    <div className="surface-card flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
        {Icon && <Icon className={`h-4 w-4 ${TONE[tone]}`} />}
      </div>
      <div className={`font-display text-2xl font-bold ${TONE[tone]}`}>{value}</div>
      {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}
