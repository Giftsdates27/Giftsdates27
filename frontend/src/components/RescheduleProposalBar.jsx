import React, { useState } from "react";
import { Button } from "./ui/button";
import { toast } from "sonner";
import { CalendarClock, Check, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { rescheduleErr } from "./RescheduleDialog";
import { myTz, zonedInstant, cityOf } from "../lib/tz";

const fromKeyLabel = (d, lang) => { const [y, m, dd] = d.split("-").map(Number); return new Date(y, m - 1, dd).toLocaleDateString(lang, { weekday: "short", day: "numeric", month: "short" }); };

/** Shows a pending new-time proposal: the other side accepts/keeps the original, the proposer can withdraw. */
export default function RescheduleProposalBar({ id, p, mine, url, otherName, onDone, wallTz }) {
  const { lang } = useApp();
  const [busy, setBusy] = useState(false);
  // VIP price-list dates: the time is the VIP's wall clock → show it as-is with the city, plus the viewer's own time if different.
  const wallStart = wallTz ? zonedInstant(p.local_day, p.local_time, wallTz) : null;
  const when = wallTz
    ? `${fromKeyLabel(p.local_day, lang)} · ${p.local_time} (${cityOf(wallTz)})${wallTz !== myTz() ? ` · ${t("tz_your_time", lang)} ${wallStart.toLocaleString(lang, { weekday: "short", hour: "2-digit", minute: "2-digit" })}` : ""}`
    : p.scheduled_start ? new Date(p.scheduled_start).toLocaleString([], { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : `${p.local_day} · ${p.local_time}`;
  const answer = async (a) => {
    setBusy(true);
    try {
      await api.post(`${url}/${a}`);
      toast.success(t(a === "accept" ? "rp_accepted" : mine ? "rsch_withdrawn" : "rp_declined", lang));
      onDone?.();
    } catch (e) { toast.error(rescheduleErr(e.response?.data?.detail, lang)); }
    finally { setBusy(false); }
  };
  return (
    <div className="mt-3 w-full rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 flex flex-wrap items-center gap-2 text-xs" data-testid={`resched-proposal-${id}`}>
      <CalendarClock size={14} className="text-amber-300" />
      <span className="text-amber-100">{mine ? t("rsch_waiting", lang) : t("rsch_asks", lang).replace("{o}", otherName || "")} <b className="font-mono-num" data-testid={`resched-when-${id}`}>{when}</b></span>
      <div className="flex gap-2 ms-auto">
        {!mine && <Button size="sm" disabled={busy} onClick={() => answer("accept")} className="bg-emerald-600 hover:bg-emerald-500 text-white border-0 h-8" data-testid={`resched-accept-${id}`}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <><Check size={14} className="me-1" />{t("rp_accept", lang)}</>}</Button>}
        <Button size="sm" variant="outline" disabled={busy} onClick={() => answer("decline")} className="bg-white/5 border-white/15 text-slate-300 h-8" data-testid={`resched-decline-${id}`}>{t(mine ? "rsch_withdraw" : "rp_keep", lang)}</Button>
      </div>
    </div>
  );
}
