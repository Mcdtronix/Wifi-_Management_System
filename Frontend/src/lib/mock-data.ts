// Mock data for the Hotspot Management System.
// Replace with API calls once the Django backend is wired in.

export type PlanTier = "Bronze" | "Silver" | "Gold" | "Platinum";

export interface Plan {
  id: string;
  name: PlanTier;
  price: number;
  durationDays: number;
  bandwidthMbps: number;
  quotaGb: number | null;
  popular?: boolean;
}

export interface Subscriber {
  id: string;
  fullName: string;
  username: string;
  phone: string;
  plan: PlanTier;
  status: "active" | "expired" | "suspended";
  expiresAt: string;
  device: string;
  usedGb: number;
  quotaGb: number | null;
}

export interface Voucher {
  id: string;
  code: string;
  plan: PlanTier;
  status: "unused" | "used" | "expired";
  createdAt: string;
}

export const PLANS: Plan[] = [
  { id: "p1", name: "Bronze", price: 1500, durationDays: 30, bandwidthMbps: 5, quotaGb: 20 },
  { id: "p2", name: "Silver", price: 2500, durationDays: 30, bandwidthMbps: 10, quotaGb: 50, popular: true },
  { id: "p3", name: "Gold", price: 4000, durationDays: 30, bandwidthMbps: 20, quotaGb: 150 },
  { id: "p4", name: "Platinum", price: 7000, durationDays: 30, bandwidthMbps: 50, quotaGb: null },
];

export const CURRENT_SUBSCRIBER: Subscriber = {
  id: "s-001",
  fullName: "John Mwangi",
  username: "jmwangi",
  phone: "+254 712 345 678",
  plan: "Silver",
  status: "active",
  expiresAt: "2026-06-22",
  device: "Samsung Galaxy A54",
  usedGb: 31.4,
  quotaGb: 50,
};

export const SUBSCRIBERS: Subscriber[] = [
  CURRENT_SUBSCRIBER,
  { id: "s-002", fullName: "Aisha Hassan", username: "aisha.h", phone: "+254 733 112 994", plan: "Gold", status: "active", expiresAt: "2026-07-04", device: "iPhone 14", usedGb: 78.2, quotaGb: 150 },
  { id: "s-003", fullName: "Brian Otieno", username: "brian.o", phone: "+254 720 558 102", plan: "Bronze", status: "expired", expiresAt: "2026-05-30", device: "Tecno Spark", usedGb: 20, quotaGb: 20 },
  { id: "s-004", fullName: "Grace Wanjiru", username: "grace.w", phone: "+254 711 887 233", plan: "Platinum", status: "active", expiresAt: "2026-06-28", device: "MacBook Pro", usedGb: 412.5, quotaGb: null },
  { id: "s-005", fullName: "Samuel Kiprono", username: "sam.k", phone: "+254 798 441 660", plan: "Silver", status: "suspended", expiresAt: "2026-06-12", device: "Xiaomi Redmi", usedGb: 50, quotaGb: 50 },
];

export const VOUCHERS: Voucher[] = [
  { id: "v1", code: "TGD-7K2P-9MX1", plan: "Silver", status: "unused", createdAt: "2026-06-01" },
  { id: "v2", code: "TGD-4N8R-2QY7", plan: "Gold", status: "used", createdAt: "2026-05-28" },
  { id: "v3", code: "TGD-9V1L-6BC3", plan: "Bronze", status: "unused", createdAt: "2026-06-04" },
  { id: "v4", code: "TGD-3F5H-8WJ2", plan: "Platinum", status: "expired", createdAt: "2026-04-15" },
];

export const ADMIN_STATS = {
  activeSubscribers: 1248,
  expiredSubscribers: 134,
  onlineUsers: 412,
  revenueToday: 84500,
  revenueMonth: 1862400,
  pendingDeviceRequests: 7,
  quotaViolations: 12,
  fraudAlerts: 3,
};
