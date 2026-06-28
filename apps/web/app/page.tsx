"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { CATS, CatKey, RecurringItem, Txn } from "./lib/demoData";
import {
  ApiCategory, Analytics,
  toTxn, toRecurring, catKey,
  fetchExpenses, fetchRecurring, fetchCategories, fetchAnalytics,
  apiDeleteRecurring, apiPatchRecurring, apiCreateRecurring, apiPatchExpense,
} from "./lib/api";
import Overview from "./components/Overview";
import Spending from "./components/Spending";
import NetWorth from "./components/NetWorth";
import Recurring from "./components/Recurring";
import Transactions from "./components/Transactions";
import { fmtINR } from "./lib/format";

type Tab = "overview" | "spending" | "networth" | "recurring" | "transactions";
type ReconState = "balanced" | "gap" | "large";
const RECON_ORDER: ReconState[] = ["balanced", "gap", "large"];

declare global {
  interface Window {
    onTelegramAuth: (user: Record<string, string>) => void;
  }
}

function isoToday() {
  return new Date().toISOString().split("T")[0];
}
function isoMonthStart() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

export default function Dashboard() {
  const [authStatus, setAuthStatus] = useState<"loading" | "authed" | "unauthed">("loading");
  const [tab, setTab] = useState<Tab>("overview");
  const [isEmpty, setIsEmpty] = useState(false);
  const [dataLoading, setDataLoading] = useState(false);
  const [reconState, setReconState] = useState<ReconState>("balanced");

  const [txns, setTxns] = useState<Txn[]>([]);
  const [recurring, setRecurring] = useState<RecurringItem[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [categories, setCategories] = useState<ApiCategory[]>([]);

  // UUID lookup maps (numeric component ID → API UUID)
  const txnUuids = useRef<Record<number, string>>({});
  const recurringUuids = useRef<Record<number, string>>({});

  async function loadData() {
    setDataLoading(true);
    try {
      const [expRes, recRes, catRes, anlRes] = await Promise.all([
        fetchExpenses(200),
        fetchRecurring(),
        fetchCategories(),
        fetchAnalytics(isoMonthStart(), isoToday()),
      ]);

      const mappedTxns = expRes.expenses.map((e, i) => {
        txnUuids.current[i + 1] = e.id;
        return toTxn(e, i);
      });
      setTxns(mappedTxns);
      setIsEmpty(mappedTxns.length === 0);

      const uuidMap: Record<number, string> = {};
      const mappedRec = recRes.items.map((r, i) => {
        uuidMap[i + 1] = r.id;
        return toRecurring(r, i);
      });
      recurringUuids.current = uuidMap;
      setRecurring(mappedRec);

      setCategories(catRes.categories);
      setAnalytics(anlRes);
    } catch {
      // if user not registered yet, show empty state
      setIsEmpty(true);
    } finally {
      setDataLoading(false);
    }
  }

  useEffect(() => {
    fetch("/api/auth")
      .then((r) => {
        if (r.ok) { setAuthStatus("authed"); loadData(); }
        else setAuthStatus("unauthed");
      })
      .catch(() => setAuthStatus("unauthed"));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Telegram Login Widget
  useEffect(() => {
    if (authStatus !== "unauthed") return;
    window.onTelegramAuth = async (user) => {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(user),
      });
      if (res.ok) { setAuthStatus("authed"); loadData(); }
    };
    const el = document.getElementById("tg-login-mount");
    if (!el || el.querySelector("script")) return;
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", "nuddgee_bot");
    script.setAttribute("data-size", "large");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    el.appendChild(script);
    return () => { window.onTelegramAuth = undefined as unknown as typeof window.onTelegramAuth; };
  }, [authStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUpdateTxns = useCallback(async (newTxns: Txn[]) => {
    // find the edited txn (same id, different values)
    const edited = newTxns.find((t) => {
      const old = txns.find((x) => x.id === t.id);
      return old && (old.amount !== t.amount || old.date !== t.date || old.cat !== t.cat || old.note !== t.note);
    });
    setTxns(newTxns);
    if (edited) {
      const uuid = txnUuids.current[edited.id];
      const cat = categories.find((c) => c.name.toLowerCase() === edited.cat);
      if (uuid) {
        await apiPatchExpense(uuid, {
          amount: Math.abs(edited.amount),
          note: edited.note || null,
          merchant: edited.merchant || null,
          spent_at: edited.date ? `${edited.date}T00:00:00` : undefined,
          ...(cat ? { category_id: cat.id } : {}),
        }).catch(console.error);
      }
    }
  }, [txns, categories]);

  const handleUpdateRecurring = useCallback(async (newItems: RecurringItem[]) => {
    const oldIds = new Set(recurring.map((r) => r.id));
    const newIds = new Set(newItems.map((r) => r.id));

    const deleted = recurring.filter((r) => !newIds.has(r.id));
    const added = newItems.filter((r) => !oldIds.has(r.id));
    const changed = newItems.filter((r) => {
      if (!oldIds.has(r.id)) return false;
      const old = recurring.find((x) => x.id === r.id);
      return old && JSON.stringify(old) !== JSON.stringify(r);
    });

    setRecurring(newItems);

    for (const item of deleted) {
      const uuid = recurringUuids.current[item.id];
      if (uuid) await apiDeleteRecurring(uuid).catch(console.error);
    }
    for (const item of changed) {
      const uuid = recurringUuids.current[item.id];
      const cat = categories.find((c) => c.name.toLowerCase() === item.cat);
      if (uuid) {
        await apiPatchRecurring(uuid, {
          name: item.name,
          amount: item.amount,
          direction: item.type,
          day_of_month: item.day,
          is_active: item.active,
          ...(cat ? { category_id: cat.id } : {}),
        }).catch(console.error);
      }
    }
    for (const item of added) {
      const cat = categories.find((c) => c.name.toLowerCase() === item.cat);
      if (!cat) continue;
      const created = await apiCreateRecurring({
        name: item.name,
        amount: item.amount,
        category_id: cat.id,
        direction: item.type,
        day_of_month: item.day,
        is_active: item.active,
      }).catch(console.error);
      if (created) recurringUuids.current[item.id] = created.id;
    }
  }, [recurring, categories]);

  const juneList = txns.filter((t) => {
    const today = isoToday();
    const monthStart = isoMonthStart();
    return t.date >= monthStart && t.date <= today;
  });
  const monthSpend = analytics?.totalSpend
    ?? juneList.filter((t) => t.amount < 0).reduce((a, t) => a + Math.abs(t.amount), 0);
  const income = recurring.filter((r) => r.type === "credit" && r.active).reduce((a, r) => a + r.amount, 0) || 120000;
  const savRate = analytics?.savingsRate != null
    ? Math.round(analytics.savingsRate * 100)
    : Math.round(((income - monthSpend) / income) * 100);
  const savColor = savRate >= 0 ? "#5f8f6f" : "#b8503f";
  const accent = "#c06a47";
  const muted = "#b3a99d";
  const tint = (k: Tab) => (tab === k ? accent : muted);

  const latestBalance = analytics?.balanceTrend?.at(-1)?.balance ?? null;

  // ── Login screen ──────────────────────────────────────────────────────────
  if (authStatus === "unauthed") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#e7e1d7", padding: "28px 16px" }}>
        <div style={{ background: "#f5f2ec", borderRadius: 32, padding: "40px 32px", maxWidth: 340, width: "100%", textAlign: "center", boxShadow: "0 20px 60px rgba(0,0,0,0.12)" }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#c06a47", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px", fontSize: 22 }}>
            <span style={{ color: "#fff", fontWeight: 800 }}>N</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, marginBottom: 8 }}>Nudge</div>
          <div style={{ fontSize: 14, color: "#8c8479", lineHeight: 1.6, marginBottom: 28 }}>
            Sign in with Telegram to view your personal finance dashboard.
          </div>
          <div id="tg-login-mount" style={{ display: "flex", justifyContent: "center" }} />
        </div>
      </div>
    );
  }

  // ── Loading screen ────────────────────────────────────────────────────────
  if (authStatus === "loading" || dataLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#e7e1d7", padding: "28px 16px", boxSizing: "border-box" }}>
        <div style={{ position: "relative", height: "min(874px, calc(100vh - 56px))", width: "100%", maxWidth: 402, display: "flex", flexDirection: "column", background: "#f5f2ec", borderRadius: 44, boxShadow: "0 30px 80px rgba(0,0,0,0.18)", overflow: "hidden", padding: "28px 18px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 14, paddingTop: 6 }}>
            <div className="shimmer" style={{ height: 150 }} />
            <div style={{ display: "flex", gap: 12 }}>
              <div className="shimmer" style={{ height: 84, flex: 1 }} />
              <div className="shimmer" style={{ height: 84, flex: 1 }} />
            </div>
            <div className="shimmer" style={{ height: 46, width: "40%" }} />
            <div className="shimmer" style={{ height: 64 }} />
            <div className="shimmer" style={{ height: 64 }} />
          </div>
        </div>
      </div>
    );
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#e7e1d7", padding: "28px 16px", boxSizing: "border-box" }}>
      <div style={{
        position: "relative", height: "min(874px, calc(100vh - 56px))", width: "100%", maxWidth: 402,
        display: "flex", flexDirection: "column",
        background: "#f5f2ec",
        fontFamily: "var(--font-hanken, 'Hanken Grotesk', system-ui, sans-serif)",
        color: "#26211c",
        WebkitFontSmoothing: "antialiased",
        borderRadius: 44,
        boxShadow: "0 30px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.08)",
        overflow: "hidden",
      }}>
        {/* Top bar */}
        <div style={{ padding: "28px 20px 12px", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#c06a47" }} />
            <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.4 }}>Nudge</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", background: "#ebe4d9", borderRadius: 9, padding: 3, gap: 2 }}>
              {(([["Live", false], ["Empty", true]] as const)).map(([label, val]) => {
                const active = isEmpty === val;
                return (
                  <button key={label} onClick={() => setIsEmpty(val)}
                    style={{ padding: "5px 11px", borderRadius: 7, fontSize: 11, fontWeight: 700, letterSpacing: "0.02em", cursor: "pointer", border: "none", background: active ? "#fff" : "transparent", color: active ? "#26211c" : "#9b9388", boxShadow: active ? "0 1px 2px rgba(0,0,0,0.08)" : "none" }}>{label}</button>
                );
              })}
            </div>
            <button
              onClick={async () => { await fetch("/api/auth", { method: "DELETE" }); setAuthStatus("unauthed"); }}
              style={{ fontSize: 11, fontWeight: 700, color: "#b0a89d", background: "none", border: "none", cursor: "pointer", padding: "5px 8px" }}
              title="Logout"
            >↩</button>
          </div>
        </div>

        {/* Scroll area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "6px 18px 22px" }}>
          {tab === "overview" && (
            <Overview txns={txns} isEmpty={isEmpty} reconState={reconState}
              onCycleRecon={() => setReconState((s) => RECON_ORDER[(RECON_ORDER.indexOf(s) + 1) % 3])}
              onGoTransactions={() => setTab("transactions")}
              balance={latestBalance ?? undefined}
            />
          )}
          {tab === "spending" && <Spending txns={txns} isEmpty={isEmpty} analytics={analytics} />}
          {tab === "networth" && <NetWorth isEmpty={isEmpty} savRate={savRate} savColor={savColor} balanceTrend={analytics?.balanceTrend} />}
          {tab === "recurring" && <Recurring items={recurring} isEmpty={isEmpty} onUpdate={handleUpdateRecurring} />}
          {tab === "transactions" && <Transactions txns={txns} isEmpty={isEmpty} onUpdateTxns={handleUpdateTxns} />}
        </div>

        {/* Bottom nav */}
        <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-around", alignItems: "flex-start", padding: "9px 6px 20px", borderTop: "1px solid #e7e1d6", background: "#fbf9f5" }}>
          <NavItem label="Overview" color={tint("overview")} onClick={() => setTab("overview")} icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><circle cx="6.5" cy="6.5" r="2.6" /><circle cx="15.5" cy="6.5" r="2.6" /><circle cx="6.5" cy="15.5" r="2.6" /><circle cx="15.5" cy="15.5" r="2.6" /></svg>} />
          <NavItem label="Spending" color={tint("spending")} onClick={() => setTab("spending")} icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><rect x="3" y="11" width="4" height="8" rx="1" /><rect x="9" y="6" width="4" height="13" rx="1" /><rect x="15" y="9" width="4" height="10" rx="1" /></svg>} />
          <NavItem label="Net worth" color={tint("networth")} onClick={() => setTab("networth")} icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M3 15l5-5 3 3 6-7" /><path d="M17 6h-4M17 6v4" /></svg>} />
          <NavItem label="Recurring" color={tint("recurring")} onClick={() => setTab("recurring")} icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M5 8a7 7 0 0 1 12-2.5M17 5.5V2.5M17 5.5h-3" /><path d="M17 14a7 7 0 0 1-12 2.5M5 16.5v3M5 16.5h3" /></svg>} />
          <NavItem label="Activity" color={tint("transactions")} onClick={() => setTab("transactions")} icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><circle cx="5" cy="6" r="1.6" /><rect x="9" y="5" width="10" height="2.2" rx="1.1" /><circle cx="5" cy="11" r="1.6" /><rect x="9" y="10" width="10" height="2.2" rx="1.1" /><circle cx="5" cy="16" r="1.6" /><rect x="9" y="15" width="10" height="2.2" rx="1.1" /></svg>} />
        </div>
      </div>
    </div>
  );
}

function NavItem({ label, color, onClick, icon }: { label: string; color: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, width: 62, cursor: "pointer", color, background: "none", border: "none", padding: 0, fontFamily: "inherit" }}>
      {icon}
      <span style={{ fontSize: 10, fontWeight: 700 }}>{label}</span>
    </button>
  );
}
