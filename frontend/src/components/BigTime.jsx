import React from "react";
import { ArrowRight, CalendarDays } from "lucide-react";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";

/** Big, easy-to-read start → finish time of a date. Times are shown as given (HH:MM). */
export default function BigTime({ day, start, end, nextDay, hours, testid }) {
  const { lang } = useApp();
  return (
    <div className="mt-2 inline-flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5" data-testid={testid}>
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
  );
}

export const hmOf = (d, lang) => d.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" });
export const dayOf = (d, lang) => d.toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" });
