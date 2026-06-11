import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/admin")({
  component: AdminLayout,
});

function AdminLayout() {
  const { session } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (session === null) {
      const t = setTimeout(() => {
        if (!localStorage.getItem("tgd_session")) navigate({ to: "/login" });
      }, 50);
      return () => clearTimeout(t);
    }
  }, [session, navigate]);

  return <Outlet />;
}
