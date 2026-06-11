// Mock auth context. Swap for real JWT auth once the backend is wired.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Role = "admin" | "subscriber";

interface Session {
  username: string;
  role: Role;
}

interface Tokens {
  access: string;
  refresh: string;
}

interface AuthValue {
  session: Session | null;
  login: (s: Session, tokens: Tokens) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);
const STORAGE_KEY = "tgd_session";
const ACCESS_TOKEN_KEY = "tgd_access_token";
const REFRESH_TOKEN_KEY = "tgd_refresh_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setSession(JSON.parse(raw));
    } catch {
      // ignore corrupt storage
    }
  }, []);

  const login = (s: Session, tokens: Tokens) => {
    setSession(s);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
  };
  const logout = () => {
    setSession(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.location.href = "/login";
  };

  return <AuthContext.Provider value={{ session, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
