import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("gd_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// A blocked time in the user's own calendar → let the upgrade offer pop up (see UnlockUpsell)
api.interceptors.response.use(null, (err) => {
  const d = err.response?.data?.detail;
  if (typeof d === "string" && d.startsWith("SLOT_LOCKED:") && d.includes("|")) {
    const [win, day, uid] = d.slice(12).split("|");
    window.dispatchEvent(new CustomEvent("gd-unlock-upsell", { detail: { day, from: win.split("-")[0], to: win.split("-")[1], uid } }));
  }
  return Promise.reject(err);
});

export function fileUrl(path) {
  if (!path) return null;
  const t = localStorage.getItem("gd_token");
  return `${API}/files/${path}?auth=${encodeURIComponent(t || "")}`;
}
