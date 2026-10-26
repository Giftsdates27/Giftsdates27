import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Button } from "./ui/button";
import { Calendar } from "./ui/calendar";
import { toast } from "sonner";
import { CalendarClock, Clock } from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { toKey, fromKey, minHm, dayWins, openDayKeys, bestDayKeys } from "../lib/availability";
import TimeChooser from "./TimeChooser";
import AvailabilityOverview from "./AvailabilityOverview";

const ERR = { DAY_UNAVAILABLE: "day_unavailable_err", TIME_PASSED: "err_time_passed", DATE_STARTED: "rsch_err_started", CANNOT_RESCHEDULE: "rsch_err_cannot" };

export const rescheduleErr = (d, lang) => {
  if (!d) return t("failed", lang);
  if (ERR[d]) return t(ERR[d], lang);
  if (d.startsWith("SLOT_LOCKED")) return t("iv_slot_locked_err", lang);
  if (d.startsWith("SLOT_BUSY") || d === "TIME_CONFLICT") return t("iv_slot_taken_err", lang);
  if (d.startsWith("TIME_UNAVAILABLE:")) return t("time_unavailable_err", lang).replace("{w}", d.split(":").slice(1).join(":"));
  return d;
};

/** Pick a new free day + start time from the invited person's calendar and send it as a proposal. */
export default function RescheduleDialog({ open, onOpenChange, ownerId, itemId, url, onDone }) {
  const { lang } = useApp();
  const [avail, setAvail] = useState({ available_days: [], busy_days: [] });
  const [day, setDay] = useState(null);
  const [start, setStart] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open || !ownerId) return;
    setDay(null); setStart(null);
    api.get(`/profiles/${ownerId}/availability`, { params: { exclude: itemId } }).then(r => setAvail(r.data)).catch(() => {});
  }, [open, ownerId, itemId]);

  const busySet = new Set(avail.busy_days || []);
  const isDisabled = (d) => {
    const k = toKey(d);
    if (d < new Date(new Date().setHours(0, 0, 0, 0)) || busySet.has(k)) return true;
    return !openDayKeys(avail).includes(k) && avail.restricted !== false;
  };

  const send = async () => {
    if (!day || start == null) { toast.error(t("iv_pick_slot_err", lang)); return; }
    setBusy(true);
    try {
      const dt = fromKey(day); dt.setHours(0, start, 0, 0);
      await api.post(url, { scheduled_start: dt.toISOString(), local_day: day, local_time: minHm(start) });
      toast.success(t("rsch_sent", lang));
      onOpenChange(false); onDone?.();
    } catch (e) { toast.error(rescheduleErr(e.response?.data?.detail, lang)); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#161320] border-white/10 text-white max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="reschedule-dialog">
        <DialogHeader>
          <DialogTitle className="font-serif-luxe text-2xl flex items-center gap-2"><CalendarClock size={20} className="text-amber-300" />{t("rsch_title", lang)}</DialogTitle>
          <DialogDescription className="text-slate-400 text-sm">{t("rsch_hint", lang)}</DialogDescription>
        </DialogHeader>
        <AvailabilityOverview avail={avail} selected={day} onPick={(k) => { setDay(k); setStart(null); }} max={8} testid="reschedule-avail" />
        <div className="rounded-xl border border-white/10 bg-white/5 inline-block" data-testid="reschedule-calendar">
          <Calendar key={day ? day.slice(0, 7) : "now"} defaultMonth={day ? fromKey(day) : undefined} mode="single" selected={day ? fromKey(day) : undefined}
            onSelect={(d) => { if (d) { setDay(toKey(d)); setStart(null); } }} disabled={isDisabled}
            modifiers={{ available: openDayKeys(avail).map(fromKey), best: bestDayKeys(avail).map(fromKey) }}
            modifiersClassNames={{ available: "ring-1 ring-emerald-400/50 rounded-md", best: "!ring-2 !ring-amber-300 rounded-md font-semibold" }}
            classNames={{ day_selected: "bg-rose-500 text-white hover:bg-rose-500 focus:bg-rose-500" }} />
        </div>
        <div>
          <label className="text-xs text-slate-400 flex items-center gap-1"><Clock size={12} /> {t("pick_start_time", lang)}{day ? ` · ${day}` : ""}</label>
          {!day ? <div className="mt-2 text-xs text-slate-500">{t("pick_day", lang)}…</div>
            : <TimeChooser key={day} day={day} wins={dayWins(avail, day)} taken={(avail.busy_slots || {})[day] || []} value={start} onChange={setStart} testid="reschedule-time" />}
        </div>
        <p className="text-[11px] text-amber-200/90 rounded-lg border border-amber-500/30 bg-amber-500/5 p-2" data-testid="reschedule-note">{t("rsch_note", lang)}</p>
        <Button data-testid="reschedule-send-button" disabled={busy || !day || start == null} onClick={send} className="rose-btn text-white border-0 w-full h-11">{t("rsch_send", lang)}</Button>
      </DialogContent>
    </Dialog>
  );
}
