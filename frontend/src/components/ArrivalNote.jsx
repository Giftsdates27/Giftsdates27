import React from "react";
import { KeyRound } from "lucide-react";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";

/** VIP's arrival instructions (door code, entrance…) — the server only sends them for confirmed dates at the VIP's place. */
export default function ArrivalNote({ note, testid }) {
  const { lang } = useApp();
  if (!note) return null;
  return (
    <div className="mt-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100 flex items-start gap-1.5" data-testid={testid}>
      <KeyRound size={13} className="mt-0.5 shrink-0 text-amber-300" />
      <div><span className="font-semibold">{t("arr_title", lang)}:</span> <span className="whitespace-pre-wrap">{note}</span></div>
    </div>
  );
}
