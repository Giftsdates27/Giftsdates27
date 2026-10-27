// Timezone helpers: show a date's time in each person's own clock.
export const myTz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { return "UTC"; } };

const offsetMin = (d, tz) => {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
    .formatToParts(d).map((x) => [x.type, x.value]));
  return (Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute) - Math.floor(d.getTime() / 60000) * 60000) / 60000;
};

/** The real instant of wall-clock `date` (YYYY-MM-DD) + `hm` (HH:MM) in timezone `tz`. */
export const zonedInstant = (date, hm, tz) => {
  const guess = new Date(`${date}T${hm}:00Z`);
  if (!tz) return new Date(`${date}T${hm}:00`);
  try {
    const o1 = offsetMin(guess, tz), d = new Date(guess.getTime() - o1 * 60000), o2 = offsetMin(d, tz);
    return o1 === o2 ? d : new Date(guess.getTime() - o2 * 60000);
  } catch { return new Date(`${date}T${hm}:00`); }
};

export const cityOf = (tz) => (tz || "").split("/").pop().replace(/_/g, " ");

export const fmtIn = (d, tz, lang, opts) => { try { return d.toLocaleString(lang, { timeZone: tz, ...opts }); } catch { return d.toLocaleString(lang, opts); } };
