"use client";
import { useState, useEffect } from "react";
import { makeTxns, SEED_RECURRING, RecurringItem, Txn } from "./lib/demoData";
import Overview from "./components/Overview";
import Spending from "./components/Spending";
import NetWorth from "./components/NetWorth";
import Recurring from "./components/Recurring";
import Transactions from "./components/Transactions";
import { fmtINR } from "./lib/format";

type Tab = "overview" | "spending" | "networth" | "recurring" | "transactions";
type ReconState = "balanced" | "gap" | "large";
const RECON_ORDER: ReconState[] = ["balanced", "gap", "large"];

const TXNS_STATIC = makeTxns();

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("overview");
  const [isEmpty, setIsEmpty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reconState, setReconState] = useState<ReconState>("balanced");
  const [recurring, setRecurring] = useState<RecurringItem[]>(SEED_RECURRING);
  const [txns, setTxns] = useState<Txn[]>(TXNS_STATIC);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 650);
    return () => clearTimeout(t);
  }, []);

  const juneList = txns.filter(t => t.date >= "2026-06-01" && t.date <= "2026-06-30");
  const monthSpend = juneList.filter(t => t.amount < 0).reduce((a, t) => a + Math.abs(t.amount), 0);
  const savRate = Math.round((120000 - monthSpend) / 120000 * 100);
  const savColor = savRate >= 0 ? "#5f8f6f" : "#b8503f";

  const accent = "#c06a47";
  const muted  = "#b3a99d";
  const tint = (k: Tab) => tab === k ? accent : muted;

  return (
    <div style={{minHeight:"100vh",display:"flex",alignItems:"center",justifyContent:"center",background:"#e7e1d7",padding:"28px 16px",boxSizing:"border-box"}}>
      {/* Phone shell */}
      <div style={{
        position:"relative",height:"min(874px, calc(100vh - 56px))",width:"100%",maxWidth:402,
        display:"flex",flexDirection:"column",
        background:"#f5f2ec",
        fontFamily:"var(--font-hanken, 'Hanken Grotesk', system-ui, sans-serif)",
        color:"#26211c",
        WebkitFontSmoothing:"antialiased",
        borderRadius:44,
        boxShadow:"0 30px 80px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.08)",
        overflow:"hidden",
      }}>

        {/* Top bar */}
        <div style={{padding:"28px 20px 12px",display:"flex",alignItems:"center",justifyContent:"space-between",flexShrink:0}}>
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <div style={{width:9,height:9,borderRadius:"50%",background:"#c06a47"}}/>
            <span style={{fontSize:18,fontWeight:800,letterSpacing:-0.4}}>Nudge</span>
          </div>
          <div style={{display:"flex",background:"#ebe4d9",borderRadius:9,padding:3,gap:2}}>
            {([["Live", false], ["Empty", true]] as const).map(([label, val]) => {
              const active = isEmpty === val;
              return (
                <button key={label} onClick={() => setIsEmpty(val)}
                  style={{padding:"5px 11px",borderRadius:7,fontSize:11,fontWeight:700,letterSpacing:"0.02em",cursor:"pointer",border:"none",
                    background: active ? "#fff" : "transparent",
                    color: active ? "#26211c" : "#9b9388",
                    boxShadow: active ? "0 1px 2px rgba(0,0,0,0.08)" : "none"
                  }}>{label}</button>
              );
            })}
          </div>
        </div>

        {/* Scroll area */}
        <div style={{flex:1,overflowY:"auto",padding:"6px 18px 22px"}}>
          {loading ? (
            <div style={{display:"flex",flexDirection:"column",gap:14,paddingTop:6}}>
              <div className="shimmer" style={{height:150}}/>
              <div style={{display:"flex",gap:12}}>
                <div className="shimmer" style={{height:84,flex:1}}/>
                <div className="shimmer" style={{height:84,flex:1}}/>
              </div>
              <div className="shimmer" style={{height:46,width:"40%"}}/>
              <div className="shimmer" style={{height:64}}/>
              <div className="shimmer" style={{height:64}}/>
              <div className="shimmer" style={{height:64}}/>
            </div>
          ) : (
            <>
              {tab === "overview" && (
                <Overview txns={txns} isEmpty={isEmpty} reconState={reconState}
                  onCycleRecon={() => setReconState(s => RECON_ORDER[(RECON_ORDER.indexOf(s)+1)%3])}
                  onGoTransactions={() => setTab("transactions")} />
              )}
              {tab === "spending" && <Spending txns={txns} isEmpty={isEmpty} />}
              {tab === "networth" && <NetWorth isEmpty={isEmpty} savRate={savRate} savColor={savColor} />}
              {tab === "recurring" && <Recurring items={recurring} isEmpty={isEmpty} onUpdate={setRecurring} />}
              {tab === "transactions" && <Transactions txns={txns} isEmpty={isEmpty} onUpdateTxns={setTxns} />}
            </>
          )}
        </div>

        {/* Bottom nav */}
        <div style={{flexShrink:0,display:"flex",justifyContent:"space-around",alignItems:"flex-start",padding:"9px 6px 20px",borderTop:"1px solid #e7e1d6",background:"#fbf9f5"}}>
          <NavItem label="Overview" color={tint("overview")} onClick={() => setTab("overview")}
            icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><circle cx="6.5" cy="6.5" r="2.6"/><circle cx="15.5" cy="6.5" r="2.6"/><circle cx="6.5" cy="15.5" r="2.6"/><circle cx="15.5" cy="15.5" r="2.6"/></svg>}/>
          <NavItem label="Spending" color={tint("spending")} onClick={() => setTab("spending")}
            icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><rect x="3" y="11" width="4" height="8" rx="1"/><rect x="9" y="6" width="4" height="13" rx="1"/><rect x="15" y="9" width="4" height="10" rx="1"/></svg>}/>
          <NavItem label="Net worth" color={tint("networth")} onClick={() => setTab("networth")}
            icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M3 15l5-5 3 3 6-7"/><path d="M17 6h-4M17 6v4"/></svg>}/>
          <NavItem label="Recurring" color={tint("recurring")} onClick={() => setTab("recurring")}
            icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round"><path d="M5 8a7 7 0 0 1 12-2.5M17 5.5V2.5M17 5.5h-3"/><path d="M17 14a7 7 0 0 1-12 2.5M5 16.5v3M5 16.5h3"/></svg>}/>
          <NavItem label="Activity" color={tint("transactions")} onClick={() => setTab("transactions")}
            icon={<svg width="22" height="22" viewBox="0 0 22 22" fill="currentColor"><circle cx="5" cy="6" r="1.6"/><rect x="9" y="5" width="10" height="2.2" rx="1.1"/><circle cx="5" cy="11" r="1.6"/><rect x="9" y="10" width="10" height="2.2" rx="1.1"/><circle cx="5" cy="16" r="1.6"/><rect x="9" y="15" width="10" height="2.2" rx="1.1"/></svg>}/>
        </div>
      </div>
    </div>
  );
}

function NavItem({ label, color, onClick, icon }: { label: string; color: string; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{display:"flex",flexDirection:"column",alignItems:"center",gap:4,width:62,cursor:"pointer",color,background:"none",border:"none",padding:0,fontFamily:"inherit"}}>
      {icon}
      <span style={{fontSize:10,fontWeight:700}}>{label}</span>
    </button>
  );
}
