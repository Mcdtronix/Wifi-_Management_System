export async function fetchApi(input: RequestInfo | URL, init?: RequestInit) {
  const token = localStorage.getItem("tgd_access_token");
  
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let finalInput = input;
  if (typeof input === "string" && input.startsWith("/api")) {
    finalInput = `http://127.0.0.1:8000${input}`;
  }

  const response = await fetch(finalInput, {
    ...init,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized (token expired), wipe session and kick to login
    localStorage.removeItem("tgd_session");
    localStorage.removeItem("tgd_access_token");
    localStorage.removeItem("tgd_refresh_token");
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  return response;
}
