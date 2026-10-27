import React from "react";
import { ArrowUpDown } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { useApp } from "../context/AppContext";
import { t } from "./i18n";

export const SORTS = ["soonest", "latest", "newest", "coins"];
const ms = (v) => { const n = v instanceof Date ? v.getTime() : new Date(v || 0).getTime(); return isNaN(n) ? 0 : n; };

/** Sort a list with `get(x) -> { start, created, coins }`. */
export const sortItems = (list, key, get) => {
  const cmp = {
    soonest: (a, b) => ms(a.start) - ms(b.start),
    latest: (a, b) => ms(b.start) - ms(a.start),
    newest: (a, b) => ms(b.created) - ms(a.created),
    coins: (a, b) => (b.coins || 0) - (a.coins || 0),
  }[key];
  return cmp ? [...list].sort((x, y) => cmp(get(x), get(y))) : list;
};

export const useSort = (storageKey) => {
  const [v, setV] = React.useState(() => { const s = localStorage.getItem(storageKey); return SORTS.includes(s) ? s : "soonest"; });
  return [v, (k) => { setV(k); localStorage.setItem(storageKey, k); }];
};

export function SortSelect({ value, onChange, testid = "sort-select" }) {
  const { lang } = useApp();
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-auto min-w-[190px] h-9 bg-white/5 border-white/10 text-slate-200 text-xs gap-2" data-testid={testid}>
        <ArrowUpDown size={13} className="text-rose-300" /><span className="text-slate-500">{t("sort_by", lang)}</span><SelectValue />
      </SelectTrigger>
      <SelectContent className="bg-[#161320] border-white/10 text-slate-200">
        {SORTS.map((k) => <SelectItem key={k} value={k} data-testid={`${testid}-${k}`}>{t(`sort_${k}`, lang)}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}
