import React, { useEffect, useState } from "react";
import { Lock, Unlock } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { openUnlockUpsell } from "./UnlockUpsell";

// one shared fetch of the user's locked times for all date cards on the page
let cache = null;
const loadLocked = () => (cache ||= api.get("/me/locked-slots").then((r) => r.data).catch(() => { cache = null; return { items: [] }; }));
const useLocked = () => {
  const [data, setData] = useState(null);
  useEffect(() => {
    let live = true;
    const run = () => loadLocked().then((d) => live && setData(d));
    const h = () => { cache = null; run(); };
    run();
    window.addEventListener("gd-slots-changed", h);
    return () => { live = false; window.removeEventListener("gd-slots-changed", h); };
  }, []);
  return data;
};

/** Shows the time a cancelled / refused / expired date still locks, with a way to reopen it. */
export default function LockedTimeNote({ refId, testid }) {
  const { lang } = useApp();
  const data = useLocked();
  const [busy, setBusy] = useState(false);
  const it = data?.items?.find((x) => (x.refs || []).includes(refId));
  if (!it) return null;
  const day = new Date(`${it.day}T12:00:00`).toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" });
  const reopen = async () => {
    if (!data.can_unlock) return openUnlockUpsell(it);
    setBusy(true);
    try {
      await api.post("/me/locked-slots/unlock", { day: it.day, time: it.from });
      toast.success(t("lt_reopened", lang));
      window.dispatchEvent(new Event("gd-slots-changed"));
    } catch (e) { toast.error(e.response?.data?.detail || t("failed", lang)); }
    finally { setBusy(false); }
  };
  return (
    <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/5 px-3 py-2.5 flex items-center gap-3 flex-wrap" data-testid={testid}>
      <Lock size={15} className="text-amber-300 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-sm text-amber-100">
          {t("lt_locked", lang)} <span className="font-mono-num" data-testid={`${testid}-time`}>{day} · {it.from}–{it.to}</span>
        </div>
        <div className="text-[11px] text-slate-400">{data.can_unlock ? t("lt_sub_premium", lang) : t("lt_sub", lang)}</div>
      </div>
      <button type="button" disabled={busy} onClick={reopen} data-testid={`${testid}-unlock`}
        className="inline-flex items-center gap-1.5 rounded-full px-3 h-8 text-xs font-medium bg-amber-500/90 text-black hover:bg-amber-400 transition-colors disabled:opacity-60">
        <Unlock size={13} />{data.can_unlock ? t("lt_reopen", lang) : t("lt_unlock_premium", lang)}
      </button>
    </div>
  );
}
