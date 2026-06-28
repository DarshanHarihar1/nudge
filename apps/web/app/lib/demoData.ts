import { isoDate, pad2 } from "./format";

export const CATS = [
  { key: "food",          name: "Food",          emoji: "🍴", cap: 8000 },
  { key: "groceries",     name: "Groceries",     emoji: "🛒", cap: 12000 },
  { key: "transport",     name: "Transport",     emoji: "🚗", cap: 4000 },
  { key: "rent",          name: "Rent",          emoji: "🏠", cap: null },
  { key: "utilities",     name: "Utilities",     emoji: "💡", cap: null },
  { key: "entertainment", name: "Entertainment", emoji: "🎬", cap: 3000 },
  { key: "shopping",      name: "Shopping",      emoji: "🛍️", cap: null },
  { key: "health",        name: "Health",        emoji: "💊", cap: null },
  { key: "subscriptions", name: "Subscriptions", emoji: "📱", cap: 2000 },
  { key: "education",     name: "Education",     emoji: "📚", cap: null },
  { key: "misc",          name: "Misc",          emoji: "📦", cap: null },
] as const;

export type CatKey = typeof CATS[number]["key"];

export interface Txn {
  id: number;
  date: string;
  amount: number;
  cat: CatKey;
  merchant: string;
  note: string;
  source: "recurring" | "telegram" | "manual";
}

export interface RecurringItem {
  id: number;
  name: string;
  amount: number;
  cat: CatKey;
  day: number;
  type: "debit" | "credit";
  active: boolean;
}

export const SNAPS = [
  { m: "Jul", v: 188400 }, { m: "Aug", v: 195200 }, { m: "Sep", v: 201000 },
  { m: "Oct", v: 198300 }, { m: "Nov", v: 210600 }, { m: "Dec", v: 219900 },
  { m: "Jan", v: 222400 }, { m: "Feb", v: 230800 }, { m: "Mar", v: 227500 },
  { m: "Apr", v: 238600 }, { m: "May", v: 243200 }, { m: "Jun", v: 247830 },
];

export const SEED_RECURRING: RecurringItem[] = [
  { id: 1, name: "Salary",            amount: 120000, cat: "misc",          day: 1,  type: "credit", active: true },
  { id: 2, name: "Rent",              amount: 35000,  cat: "rent",          day: 1,  type: "debit",  active: true },
  { id: 3, name: "Cult.fit",          amount: 2000,   cat: "health",        day: 3,  type: "debit",  active: true },
  { id: 4, name: "Netflix",           amount: 649,    cat: "subscriptions", day: 5,  type: "debit",  active: true },
  { id: 5, name: "Spotify",           amount: 119,    cat: "subscriptions", day: 5,  type: "debit",  active: false },
  { id: 6, name: "Electricity (BESCOM)", amount: 1850, cat: "utilities",   day: 8,  type: "debit",  active: true },
  { id: 7, name: "Internet (ACT)",    amount: 1199,   cat: "utilities",     day: 10, type: "debit",  active: true },
];

function lcg(seed: number) {
  let s = seed;
  return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
}

export function makeTxns(): Txn[] {
  const r = lcg(778291);
  const pick = <T>(a: T[]): T => a[Math.floor(r() * a.length)];
  const amt = (lo: number, hi: number) => Math.round(lo + r() * (hi - lo));

  const merch: Record<string, string[]> = {
    food:          ["Swiggy","Zomato","Blue Tokai","Third Wave","Leon Grill","Truffles"],
    groceries:     ["Zepto","Blinkit","BigBasket","DMart"],
    transport:     ["Uber","Ola","Indian Oil","Namma Metro","Rapido"],
    entertainment: ["PVR Cinemas","BookMyShow","Steam"],
    shopping:      ["Amazon","Myntra","Croma","IKEA","Nykaa"],
    health:        ["Apollo Pharmacy","1mg","Practo"],
    misc:          ["ATM Withdrawal","UPI Transfer","Urban Company"],
  };
  const notes: Record<string, string[]> = {
    food:          ["lunch with team","dinner","coffee run","weekend brunch","",""],
    groceries:     ["weekly groceries","quick top-up","",""],
    transport:     ["ride home","fuel","metro card","",""],
    entertainment: ["movie night","concert","",""],
    shopping:      ["","new headphones","home stuff",""],
    health:        ["meds","consult","",""],
    misc:          ["","cash","repair",""],
  };
  const ranges: Record<string, [number,number]> = {
    food:[150,900], groceries:[300,1900], transport:[60,720],
    entertainment:[250,1300], shopping:[700,9500], health:[300,2400], misc:[200,4200],
  };
  const dayCats = ["food","food","groceries","transport","transport","entertainment","shopping","health","misc"];

  const out: Txn[] = [];
  let id = 1;
  const months = [[2026,4,30],[2026,5,31],[2026,6,28]];

  for (const [y,m,maxd] of months) {
    out.push({ id:id++, date:isoDate(y,m,1),  amount: 120000, cat:"misc",          merchant:"Acme Corp Payroll",  note:"Monthly salary",  source:"recurring" });
    out.push({ id:id++, date:isoDate(y,m,1),  amount:-35000,  cat:"rent",          merchant:"Landlord",           note:"Monthly rent",    source:"recurring" });
    out.push({ id:id++, date:isoDate(y,m,3),  amount:-2000,   cat:"health",        merchant:"Cult.fit",           note:"Membership",      source:"recurring" });
    out.push({ id:id++, date:isoDate(y,m,5),  amount:-649,    cat:"subscriptions", merchant:"Netflix",            note:"",                source:"recurring" });
    out.push({ id:id++, date:isoDate(y,m,8),  amount:-amt(1600,2100), cat:"utilities", merchant:"BESCOM",         note:"Electricity",     source:"recurring" });
    out.push({ id:id++, date:isoDate(y,m,10), amount:-1199,   cat:"utilities",     merchant:"ACT Fibernet",       note:"Internet",        source:"recurring" });
    for (let d = 1; d <= maxd; d++) {
      const c0 = r();
      const count = c0 < 0.33 ? 0 : c0 < 0.72 ? 1 : 2;
      for (let k = 0; k < count; k++) {
        const c = pick(dayCats) as CatKey;
        const [lo, hi] = ranges[c];
        const src = r() < 0.68 ? "telegram" : "manual";
        out.push({ id:id++, date:isoDate(y,m,d), amount:-amt(lo,hi), cat:c, merchant:pick(merch[c]), note:pick(notes[c]), source:src as "telegram"|"manual" });
      }
    }
  }
  return out.sort((a, b) => a.date < b.date ? 1 : a.date > b.date ? -1 : b.id - a.id);
}
