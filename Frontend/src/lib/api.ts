import { fetchApi } from "./apiClient";

export const Api = {
  auth: {
    requestPasswordReset: async (payload: { username: string; phone_number: string }) => {
      const res = await fetchApi("/api/v1/subscribers/auth/password-reset/request/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to request reset.");
      }
      return res.json();
    },
    confirmPasswordReset: async (payload: any) => {
      const res = await fetchApi("/api/v1/subscribers/auth/password-reset/confirm/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || error.otp || error.confirm_password || "Failed to reset password.");
      }
      return res.json();
    },
    adminLogin: async (payload: any) => {
      const res = await fetchApi("/api/v1/auth/login/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Invalid admin credentials");
      }
      return res.json();
    },
    subscriberLogin: async (payload: any) => {
      const res = await fetchApi("/api/v1/subscribers/auth/login/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Invalid subscriber credentials");
      }
      return res.json();
    },
  },
  
  dashboard: {
    getStats: async () => {
      const res = await fetchApi("/api/v1/reporting/dashboard/");
      if (!res.ok) throw new Error("Failed to fetch dashboard stats");
      return res.json();
    },
  },
  
  subscribers: {
    list: async () => {
      const res = await fetchApi("/api/v1/subscribers/");
      if (!res.ok) throw new Error("Failed to fetch subscribers");
      return res.json();
    },
    // Used by subscriber portal to fetch their own details
    me: async () => {
      // For now we get the first subscriber matching current session, 
      // but ideally the backend has a /me/ endpoint.
      // We will assume the backend /api/v1/subscribers/ returns the current user's profile if they are a subscriber.
      const res = await fetchApi("/api/v1/subscribers/me/");
      if (!res.ok) throw new Error("Failed to fetch profile");
      const data = await res.json();
      return data;
    },
  },

  plans: {
    list: async () => {
      const res = await fetchApi("/api/v1/plans/");
      if (!res.ok) throw new Error("Failed to fetch plans");
      return res.json();
    },
  },

  vouchers: {
    list: async () => {
      const res = await fetchApi("/api/v1/vouchers/");
      if (!res.ok) throw new Error("Failed to fetch vouchers");
      return res.json();
    },
  },

  quota: {
    getUsage: async () => {
      // In a real app, you might pass subscriberId or rely on backend session
      const res = await fetchApi("/api/v1/reporting/bandwidth/");
      if (!res.ok) throw new Error("Failed to fetch usage");
      return res.json();
    },
  },

  devices: {
    listRequests: async () => {
      const res = await fetchApi("/api/v1/devices/");
      if (!res.ok) throw new Error("Failed to fetch devices");
      return res.json();
    },
  },
};
