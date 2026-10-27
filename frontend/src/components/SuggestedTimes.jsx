import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";

const fmtDay = (d, lang) => { try { const [y, m, dd] = d.split("-").map(Number); return new Date(y, m - 1, dd).toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" }); } catch { return d; } };
const hmMin = (hm) => { const [h, m] = hm.split(":").map(Number); return h * 60 + m; };
const hhmm = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
// Regular-date suggestions carry an exact UTC start: show them in the viewer's own clock (same as the date cards).
const label = (s, lang) => {
  if (!s.scheduled_start || s.wall) return { day: fmtDay(s.date, lang), time: `${s.start}–${s.end}` };
  const a = new Date(s.scheduled_start), dur = ((hmMin(s.end) - hmMin(s.start)) + 1440) % 1440 || 150;
  return { day: a.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" }), time: `${hhmm(a)}–${hhmm(new Date(a.getTime() + dur * 60000))}` };
};

/** Nearest free times (fetched from `url`) as one-tap chips; onPick(s) sends the chosen time. Hidden when none. */
export default function SuggestedTimes({ url, onPick, title = "dl_quick_times", testid = "suggested-times", tone = "emerald" }) {
  const { lang } = useApp();
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(null);
  useEffect(() => {
    setItems(null);
    if (url) api.get(url).then((r) => setItems(r.data.suggestions || [])).catch(() => setItems([]));
  }, [url]);
  if (items === null) return <div className="text-[11px] text-slate-500 flex items-center gap-1.5"><Loader2 size={12} className="animate-spin" />{t("st_loading", lang)}</div>;
  if (!items.length) return null;
  const c = tone === "amber" ? "border-amber-500/40 bg-amber-500/10 hover:bg-amber-500/25 text-amber-100" : "border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/25 text-emerald-100";
  const pick = async (s, i) => { setBusy(i); try { await onPick(s); } catch { /* caller shows the error */ } finally { setBusy(null); } };
  return (
    <div className="space-y-1.5" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-wider opacity-80">{t(title, lang)}</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
        {items.map((s, i) => (
          <button key={`${s.date}-${s.start}`} type="button" disabled={busy !== null} onClick={() => pick(s, i)} data-testid={`${testid}-${i}`}
            className={`rounded-lg border px-2 py-1.5 text-start transition-colors disabled:opacity-50 ${c}`}>
            <div className="text-[11px] font-medium flex items-center gap-1">{busy === i && <Loader2 size={11} className="animate-spin" />}{label(s, lang).day}</div>
            <div className="text-[11px] font-mono-num text-white">{label(s, lang).time}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
