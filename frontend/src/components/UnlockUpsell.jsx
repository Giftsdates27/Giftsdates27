import React, { useCallback, useEffect, useState } from "react";
import { Crown, Lock, Coins, CreditCard, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";
import { Button } from "./ui/button";
import { api } from "../lib/api";
import { useApp } from "../context/AppContext";
import { t } from "../lib/i18n";

const PENDING = "gd_pending_unlock";
export const hasPremium = (u) => !!(u && (u.is_premium || u.is_premium_lite || u.is_vip));
/** Open the upgrade offer from anywhere: slot = { day, from, to } or { all: true }. */
export const openUnlockUpsell = (slot) => window.dispatchEvent(new CustomEvent("gd-unlock-upsell", { detail: slot }));

const unlockSlot = async (slot) => {
  if (slot.all) return api.post("/me/locked-slots/unlock-all");
  return api.post("/me/locked-slots/unlock", { day: slot.day, time: slot.from });
};

function PlanRow({ tier, name, perks, coins, usd, balance, busy, onCoins, onCard }) {
  const { lang } = useApp();
  const enough = balance >= coins;
  return (
    <div className={`rounded-xl border p-4 ${tier === "premium" ? "border-amber-500/40 bg-amber-500/5" : "border-sky-500/40 bg-sky-500/5"}`} data-testid={`uu-plan-${tier}`}>
      <div className="flex items-center gap-2">
        {tier === "premium" ? <Crown size={16} className="text-amber-300" /> : <Sparkles size={16} className="text-sky-300" />}
        <span className="font-serif-luxe text-lg">{name}</span>
        <span className="ms-auto text-[11px] text-slate-400">{t("uu_month", lang)}</span>
      </div>
      <p className="text-xs text-slate-400 mt-1">{perks}</p>
      {enough
        ? <Button disabled={!!busy} onClick={onCoins} data-testid={`uu-pay-coins-${tier}`}
            className={`mt-3 w-full h-10 text-white border-0 transition-colors ${tier === "premium" ? "rose-btn" : "bg-sky-600 hover:bg-sky-500"}`}>
            <Coins size={14} className="me-1.5" />{t("uu_pay_coins", lang)} 🪙 {coins}
          </Button>
        : <>
            <p className="mt-2 text-[11px] text-amber-200/80" data-testid={`uu-low-coins-${tier}`}>{t("uu_low_coins", lang)}</p>
            <Button disabled={!!busy} onClick={onCard} data-testid={`uu-pay-card-${tier}`} variant="outline"
              className="mt-1.5 w-full h-10 bg-white/5 border-white/20 text-white hover:bg-white/10">
              <CreditCard size={14} className="me-1.5" />{t("uu_pay_card", lang)} · ${usd}
            </Button>
          </>}
    </div>
  );
}

export default function UnlockUpsell() {
  const { user, meta, lang, refreshUser } = useApp();
  const [slot, setSlot] = useState(null);
  const [busy, setBusy] = useState(null);

  const done = useCallback(async (s, onUnlocked) => {
    try { await unlockSlot(s); } catch { /* slot may already be free */ }
    localStorage.removeItem(PENDING);
    toast.success(s.all ? t("uu_done_all", lang) : t("uu_done", lang).replace("{w}", `${s.day} ${s.from}`));
    window.dispatchEvent(new Event("gd-slots-changed"));
    onUnlocked && onUnlocked();
  }, [lang]);

  useEffect(() => {
    const h = (e) => {
      const s = e.detail || {};
      if (s.uid && user && s.uid !== user.id) return;  // the other person's blocked time — upgrading can't open it
      if (user && !hasPremium(user)) setSlot(s);
    };
    window.addEventListener("gd-unlock-upsell", h);
    return () => window.removeEventListener("gd-unlock-upsell", h);
  }, [user]);

  // back from card checkout → once premium is active, unlock the time the user was after
  useEffect(() => {
    const raw = localStorage.getItem(PENDING);
    if (raw && hasPremium(user)) done(JSON.parse(raw));
  }, [user, done]);

  const payCoins = async (tier) => {
    setBusy(tier);
    try {
      await api.post("/premium/buy-with-coins", { tier });
      await refreshUser();
      const s = slot; setSlot(null);
      await done(s);
    } catch (e) { toast.error(e.response?.data?.detail || t("failed", lang)); }
    finally { setBusy(null); }
  };

  const payCard = async (tier) => {
    setBusy(tier);
    try {
      localStorage.setItem(PENDING, JSON.stringify(slot));
      const { data } = await api.post("/payments/checkout", { package_id: tier === "premium" ? "premium_monthly" : "premium_lite_monthly", origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (e) { localStorage.removeItem(PENDING); toast.error(e.response?.data?.detail || t("failed", lang)); setBusy(null); }
  };

  if (!slot) return null;
  const balance = (user?.coins || 0) + (user?.withdrawable || 0);
  return (
    <Dialog open={!!slot} onOpenChange={(o) => !o && !busy && setSlot(null)}>
      <DialogContent className="bg-[#14121a] border-white/10 text-white max-w-md" data-testid="unlock-upsell">
        <DialogHeader>
          <DialogTitle className="font-serif-luxe text-2xl flex items-center gap-2"><Lock size={18} className="text-rose-300" />{t("uu_title", lang)}</DialogTitle>
          <DialogDescription className="text-slate-400" data-testid="uu-sub">
            {slot.all ? t("uu_sub_all", lang) : t("uu_sub", lang).replace("{w}", `${slot.day} · ${slot.from}${slot.to ? `–${slot.to}` : ""}`)}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <PlanRow tier="premium_lite" name={t("premium_lite", lang)} perks={t("uu_lite_perks", lang)} coins={meta?.premium_lite_coins || 150} usd={meta?.premium_lite?.amount || 14.99}
            balance={balance} busy={busy} onCoins={() => payCoins("premium_lite")} onCard={() => payCard("premium_lite")} />
          <PlanRow tier="premium" name="Premium" perks={t("uu_premium_perks", lang)} coins={meta?.premium_coins || 300} usd={meta?.premium?.amount || 29.99}
            balance={balance} busy={busy} onCoins={() => payCoins("premium")} onCard={() => payCard("premium")} />
        </div>
        <Button variant="ghost" disabled={!!busy} onClick={() => setSlot(null)} data-testid="uu-later" className="w-full text-slate-400 hover:text-white">{t("uu_later", lang)}</Button>
      </DialogContent>
    </Dialog>
  );
}
