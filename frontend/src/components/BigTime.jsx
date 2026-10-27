import React, { useEffect, useState } from "react";
import { ArrowRight, CalendarDays, Timer } from "lucide-react";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";

const useNow = (ms = 30000) => {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const iv = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(iv); }, [ms]);
  return now;
};

/** "Starts in 2h 15m" when the date begins within 24h, "In progress" while it runs. */
function Countdown({ startAt, endAt, testid }) {
  const { lang } = useApp();
  const now = useNow(15000);
  if (!startAt || isNaN(startAt)) return null;
  const left = startAt.getTime() - now;
  const fmt = (ms) => { const m = Math.ceil(ms / 60000), h = Math.floor(m / 60); return h ? `${h}h ${String(m % 60).padStart(2, "0")}m` : `${m}m`; };
  if (left > 0 && left <= 24 * 3600000) {
    const m = Math.ceil(left / 60000), txt = fmt(left);
    return <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border font-mono-num ${m <= 60 ? "bg-rose-500/15 border-rose-500/50 text-rose-200 animate-pulse" : "bg-emerald-500/10 border-emerald-500/40 text-emerald-200"}`} data-testid={testid}>
      <Timer size={12} />{t("cd_starts_in", lang)} {txt}</span>;
  }
  if (left <= 0 && endAt && now < endAt.getTime()) return <span className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border bg-emerald-500/20 border-emerald-500/50 text-emerald-200" data-testid={testid}><Timer size={12} />{t("ext_in_progress", lang)} · {t("cd_ends_in", lang)} <span className="font-mono-num" data-testid={`${testid}-left`}>{fmt(endAt.getTime() - now)}</span></span>;
  return null;
}

/** Big, easy-to-read start → finish time of a date. Times are shown as given (HH:MM). */
export default function BigTime({ day, start, end, nextDay, hours, startAt, endAt, testid }) {
  const { lang } = useApp();
  return (
    <div className="mt-2">
      {startAt && <div className="mb-1.5"><Countdown startAt={startAt} endAt={endAt} testid={`${testid}-countdown`} /></div>}
      <div className="inline-flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5" data-testid={testid}>
        {day && <div className="flex items-center gap-1.5 text-sm text-slate-200" data-testid={`${testid}-day`}><CalendarDays size={15} className="text-rose-300" />{day}</div>}
        <div className="flex items-center gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">{t("bk_start", lang)}</div>
            <div className="font-mono-num text-3xl leading-none text-white" data-testid={`${testid}-start`}>{start}</div>
          </div>
          <ArrowRight size={18} className="text-rose-300 mt-3" />
          <div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">{t("bk_finish", lang)}</div>
            <div className="font-mono-num text-3xl leading-none text-white" data-testid={`${testid}-end`}>{end}{nextDay && <sup className="text-xs text-amber-300 ms-0.5">+1</sup>}</div>
          </div>
          {hours ? <span className="ms-1 mt-3 text-[11px] px-1.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-200 font-mono-num">{hours}h</span> : null}
        </div>
      </div>
    </div>
  );
}

export const hmOf = (d, lang) => d.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
export const dayOf = (d, lang) => d.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" });
