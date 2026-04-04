const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  dashboard: {
    stats: () => fetchApi<import("./types").DashboardStats>("/api/dashboard/stats"),
    alerts: () => fetchApi<import("./types").RenewalAlert[]>("/api/dashboard/alerts"),
    activity: () => fetchApi<import("./types").ActivityEntry[]>("/api/dashboard/activity"),
  },
  clients: {
    list: (kanaPrefix?: string) =>
      fetchApi<import("./types").ClientSummary[]>(
        `/api/clients${kanaPrefix ? `?kana_prefix=${kanaPrefix}` : ""}`
      ),
    get: (name: string) => fetchApi(`/api/clients/${encodeURIComponent(name)}`),
    emergency: (name: string) => fetchApi(`/api/clients/${encodeURIComponent(name)}/emergency`),
    logs: (name: string) => fetchApi(`/api/clients/${encodeURIComponent(name)}/logs`),
  },
  system: {
    status: () => fetchApi<import("./types").ModelStatus>("/api/system/status"),
    loadModel: (name: string) => fetchApi(`/api/system/models/${name}/load`, { method: "POST" }),
    unloadModel: (name: string) => fetchApi(`/api/system/models/${name}/unload`, { method: "POST" }),
  },
  narratives: {
    extract: (text: string, clientName?: string) =>
      fetchApi("/api/narratives/extract", {
        method: "POST",
        body: JSON.stringify({ text, client_name: clientName }),
      }),
    upload: async (file: File): Promise<{ filename: string; text: string }> => {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/api/narratives/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload error: ${res.status}`);
      return res.json();
    },
    register: (graph: import("./types").ExtractedGraph) =>
      fetchApi("/api/narratives/register", {
        method: "POST",
        body: JSON.stringify(graph),
      }),
  },
  quicklog: {
    create: (data: { client_name: string; note: string; situation?: string }) =>
      fetchApi("/api/quicklog", { method: "POST", body: JSON.stringify(data) }),
  },
};
