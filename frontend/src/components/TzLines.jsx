import React from "react";
import { Globe2 } from "lucide-react";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { cityOf, fmtIn } from "../lib/tz";

/** Extra lines with the date's time in other people's clocks (only for timezones different from the one already shown). */
export default function TzLines({ start, end, shownTz, people = [], testid = "tz-lines" }) {
  const { lang } = useApp();
  if (!start || isNaN(start)) return null;
  const seen = new Set([shownTz]);
  const rows = people.filter((p) => p.tz && !seen.has(p.tz) && seen.add(p.tz));
  if (!rows.length) return null;
  const day = (tz) => fmtIn(start, tz, lang, { weekday: "short", day: "numeric", month: "short" });
  const hm = (d, tz) => fmtIn(d, tz, lang, { hour: "2-digit", minute: "2-digit" });
  return (
    <div className="mt-1.5 space-y-0.5" data-testid={testid}>
      {rows.map((p, i) => (
        <div key={p.tz} className="text-[11px] text-sky-200/90 flex items-center gap-1.5 flex-wrap" data-testid={`${testid}-${i}`}>
          <Globe2 size={11} className="text-sky-300" />
          <span className="text-slate-400">{p.label}:</span>
          <b className="font-mono-num text-sky-100">{day(p.tz)} · {hm(start, p.tz)}{end ? `–${hm(end, p.tz)}` : ""}</b>
          <span className="text-slate-500">({cityOf(p.tz)})</span>
        </div>
      ))}
    </div>
  );
}

export const tzLabel = (lang, name) => (name ? t("tz_their_time", lang).replace("{n}", name) : t("tz_your_time", lang));
