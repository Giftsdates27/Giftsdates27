// Curated country list with flag emojis. "Global" is a special value meaning worldwide / not tied to one country.
export const GLOBAL = "Global";

export const COUNTRIES = [
  { name: "United States", flag: "🇺🇸" },
  { name: "United Kingdom", flag: "🇬🇧" },
  { name: "Canada", flag: "🇨🇦" },
  { name: "Australia", flag: "🇦🇺" },
  { name: "Germany", flag: "🇩🇪" },
  { name: "France", flag: "🇫🇷" },
  { name: "Italy", flag: "🇮🇹" },
  { name: "Spain", flag: "🇪🇸" },
  { name: "Portugal", flag: "🇵🇹" },
  { name: "Netherlands", flag: "🇳🇱" },
  { name: "Belgium", flag: "🇧🇪" },
  { name: "Switzerland", flag: "🇨🇭" },
  { name: "Austria", flag: "🇦🇹" },
  { name: "Ireland", flag: "🇮🇪" },
  { name: "Sweden", flag: "🇸🇪" },
  { name: "Norway", flag: "🇳🇴" },
  { name: "Denmark", flag: "🇩🇰" },
  { name: "Finland", flag: "🇫🇮" },
  { name: "Iceland", flag: "🇮🇸" },
  { name: "Poland", flag: "🇵🇱" },
  { name: "Czechia", flag: "🇨🇿" },
  { name: "Slovakia", flag: "🇸🇰" },
  { name: "Hungary", flag: "🇭🇺" },
  { name: "Romania", flag: "🇷🇴" },
  { name: "Bulgaria", flag: "🇧🇬" },
  { name: "Greece", flag: "🇬🇷" },
  { name: "Croatia", flag: "🇭🇷" },
  { name: "Serbia", flag: "🇷🇸" },
  { name: "Slovenia", flag: "🇸🇮" },
  { name: "Ukraine", flag: "🇺🇦" },
  { name: "Russia", flag: "🇷🇺" },
  { name: "Belarus", flag: "🇧🇾" },
  { name: "Lithuania", flag: "🇱🇹" },
  { name: "Latvia", flag: "🇱🇻" },
  { name: "Estonia", flag: "🇪🇪" },
  { name: "Turkey", flag: "🇹🇷" },
  { name: "Georgia", flag: "🇬🇪" },
  { name: "Armenia", flag: "🇦🇲" },
  { name: "Azerbaijan", flag: "🇦🇿" },
  { name: "Kazakhstan", flag: "🇰🇿" },
  { name: "Uzbekistan", flag: "🇺🇿" },
  { name: "United Arab Emirates", flag: "🇦🇪" },
  { name: "Saudi Arabia", flag: "🇸🇦" },
  { name: "Qatar", flag: "🇶🇦" },
  { name: "Kuwait", flag: "🇰🇼" },
  { name: "Bahrain", flag: "🇧🇭" },
  { name: "Oman", flag: "🇴🇲" },
  { name: "Israel", flag: "🇮🇱" },
  { name: "Lebanon", flag: "🇱🇧" },
  { name: "Jordan", flag: "🇯🇴" },
  { name: "Egypt", flag: "🇪🇬" },
  { name: "Morocco", flag: "🇲🇦" },
  { name: "Tunisia", flag: "🇹🇳" },
  { name: "Algeria", flag: "🇩🇿" },
  { name: "Nigeria", flag: "🇳🇬" },
  { name: "Ghana", flag: "🇬🇭" },
  { name: "Kenya", flag: "🇰🇪" },
  { name: "South Africa", flag: "🇿🇦" },
  { name: "Ethiopia", flag: "🇪🇹" },
  { name: "Tanzania", flag: "🇹🇿" },
  { name: "Uganda", flag: "🇺🇬" },
  { name: "India", flag: "🇮🇳" },
  { name: "Pakistan", flag: "🇵🇰" },
  { name: "Bangladesh", flag: "🇧🇩" },
  { name: "Sri Lanka", flag: "🇱🇰" },
  { name: "Nepal", flag: "🇳🇵" },
  { name: "China", flag: "🇨🇳" },
  { name: "Hong Kong", flag: "🇭🇰" },
  { name: "Taiwan", flag: "🇹🇼" },
  { name: "Japan", flag: "🇯🇵" },
  { name: "South Korea", flag: "🇰🇷" },
  { name: "Thailand", flag: "🇹🇭" },
  { name: "Vietnam", flag: "🇻🇳" },
  { name: "Philippines", flag: "🇵🇭" },
  { name: "Indonesia", flag: "🇮🇩" },
  { name: "Malaysia", flag: "🇲🇾" },
  { name: "Singapore", flag: "🇸🇬" },
  { name: "Cambodia", flag: "🇰🇭" },
  { name: "Myanmar", flag: "🇲🇲" },
  { name: "New Zealand", flag: "🇳🇿" },
  { name: "Mexico", flag: "🇲🇽" },
  { name: "Brazil", flag: "🇧🇷" },
  { name: "Argentina", flag: "🇦🇷" },
  { name: "Chile", flag: "🇨🇱" },
  { name: "Colombia", flag: "🇨🇴" },
  { name: "Peru", flag: "🇵🇪" },
  { name: "Venezuela", flag: "🇻🇪" },
  { name: "Ecuador", flag: "🇪🇨" },
  { name: "Uruguay", flag: "🇺🇾" },
  { name: "Paraguay", flag: "🇵🇾" },
  { name: "Bolivia", flag: "🇧🇴" },
  { name: "Costa Rica", flag: "🇨🇷" },
  { name: "Panama", flag: "🇵🇦" },
  { name: "Dominican Republic", flag: "🇩🇴" },
  { name: "Cuba", flag: "🇨🇺" },
  { name: "Jamaica", flag: "🇯🇲" },
];

export const countryFlag = (name) => {
  const c = COUNTRIES.find((x) => x.name.toLowerCase() === (name || "").toLowerCase());
  return c ? c.flag : "";
};

// Map a detected/reverse-geocoded country name to a name in COUNTRIES.
// Handles common aliases and official long-form names.
const COUNTRY_ALIASES = {
  "united states of america": "United States",
  "usa": "United States",
  "us": "United States",
  "united kingdom of great britain and northern ireland": "United Kingdom",
  "great britain": "United Kingdom",
  "uk": "United Kingdom",
  "russian federation": "Russia",
  "czech republic": "Czechia",
  "republic of korea": "South Korea",
  "korea (republic of)": "South Korea",
  "korea, republic of": "South Korea",
  "uae": "United Arab Emirates",
  "united arab emirates (the)": "United Arab Emirates",
  "viet nam": "Vietnam",
  "türkiye": "Turkey",
  "turkiye": "Turkey",
  "hong kong sar china": "Hong Kong",
  "hong kong sar": "Hong Kong",
};

export const normalizeCountry = (detected) => {
  const raw = (detected || "").trim();
  if (!raw) return "";
  const d = raw.toLowerCase();
  const exact = COUNTRIES.find((c) => c.name.toLowerCase() === d);
  if (exact) return exact.name;
  if (COUNTRY_ALIASES[d]) return COUNTRY_ALIASES[d];
  const partial = COUNTRIES.find((c) => {
    const lc = c.name.toLowerCase();
    return d.includes(lc) || lc.includes(d);
  });
  return partial ? partial.name : raw;
};

// Every country (ISO 3166-1) for address forms: the curated list first, then all the others A–Z.
const ISO2 = "AD AE AF AG AI AL AM AO AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BW BY BZ CA CD CF CG CH CI CK CL CM CN CO CR CU CV CW CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GT GU GW GY HK HN HR HT HU ID IE IL IM IN IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TG TH TJ TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW".split(" ");
const flagOf = (cc) => String.fromCodePoint(...[...cc].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
export const ALL_COUNTRIES = (() => {
  let dn = null;
  try { dn = new Intl.DisplayNames(["en"], { type: "region" }); } catch { return COUNTRIES; }
  const have = new Set(COUNTRIES.map((c) => c.name.toLowerCase()));
  const norm = (n) => COUNTRY_ALIASES[(n || "").toLowerCase()] || n;
  const extra = ISO2.map((cc) => ({ name: norm(dn.of(cc)), flag: flagOf(cc) }))
    .filter((c) => c.name && !have.has(c.name.toLowerCase()) && have.add(c.name.toLowerCase()))
    .sort((a, b) => a.name.localeCompare(b.name));
  return [...COUNTRIES, ...extra];
})();
