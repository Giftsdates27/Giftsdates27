import React from "react";
import { ShieldAlert } from "lucide-react";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";
import { cancelSplit } from "./CancelPreviewDialog";

/** Exact coins the client loses if they cancel a VIP booking (50% back, 25% VIP, 25% fee; taxi always refunded). */
export default function CancelLossNote({ total = 0, taxi = 0, testid = "cancel-loss-note" }) {
  const { lang } = useApp();
  const { refund, comp, fee } = cancelSplit(total, true, taxi);
  const fill = (k) => t(k, lang).replace("{lose}", comp + fee).replace("{back}", refund).replace("{vip}", comp).replace("{fee}", fee).replace("{total}", total);
  return (
    <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-2.5 text-xs text-rose-100 flex items-start gap-2" data-testid={testid}>
      <ShieldAlert size={14} className="mt-0.5 shrink-0 text-rose-300" />
      <div className="space-y-0.5">
        <div className="font-semibold" data-testid={`${testid}-lose`}>{fill("cl_lose")}</div>
        <div className="text-rose-200/80">{fill("cl_detail")}</div>
        {taxi > 0 && <div className="text-rose-200/80">{t("cl_taxi", lang)}</div>}
        <div className="text-emerald-200/90">{fill("cl_vip_cancel")}</div>
      </div>
    </div>
  );
}
