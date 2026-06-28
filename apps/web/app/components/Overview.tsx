"use client";
import { CATS, SNAPS, Txn } from "../lib/demoData";
import { fmtINR, fmtSigned, dateShort } from "../lib/format";

type ReconState = "balanced" | "gap" | "large";

const RECON_MAP = {
  balanced: { icon:"✅", label:"Balanced",          fg:"#4f7d5f", bg:"#e7efe7", sub:"Your recorded balance matches tracked activity." },
  gap:      { icon:"⚠️", label:`Gap ${fmtINR(1240)}`, fg:"#9a7327", bg:"#f4ebd9", sub:`A ${fmtINR(1240)} gap between recorded and tracked. Add the missing entry.` },
  large:    { icon:"🔴", label:`Gap ${fmtINR(18600)}`, fg:"#a5453a", bg:"#f4e2dd", sub:`Large ${fmtINR(18600)} gap — recorded balance and activity diverge.` },
};
const RECON_ORDER: ReconState[] = ["balanced","gap","large"];

interface Props {
  txns: Txn[];
  isEmpty: boolean;
  reconState: ReconState;
  onCycleRecon: () => void;
  onGoTransactions: () => void;
  balance?: number;
}

export default function Overview({ txns, isEmpty, reconState, onCycleRecon, onGoTransactions, balance }: Props) {
  const catOf = (key: string) => CATS.find(c => c.key === key) ?? { emoji:"📦", name:"Misc", cap:null };

  const juneList = txns.filter(t => t.date >= "2026-06-01" && t.date <= "2026-06-30");
  const monthSpend = juneList.filter(t => t.amount < 0).reduce((a, t) => a + Math.abs(t.amount), 0);
  const income = 120000;
  const savRate = Math.round((income - monthSpend) / income * 100);
  const savColor = savRate >= 0 ? "#5f8f6f" : "#b8503f";

  const recent = txns.slice(0, 5).map((t, i) => {
    const c = catOf(t.cat);
    return {
      emoji: c.emoji,
      merchant: t.merchant,
      sub: dateShort(t.date) + (t.note ? " · " + t.note : " · " + c.name),
      amountText: fmtSigned(t.amount),
      amountColor: t.amount < 0 ? "#26211c" : "#5f8f6f",
      sep: i === 0 ? "transparent" : "#f0ebe2",
    };
  });

  const r = RECON_MAP[reconState];

  return (
    <div className="screen-enter">
      {isEmpty ? (
        <>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:22,padding:"28px 22px",textAlign:"center"}}>
            <div style={{fontSize:30,marginBottom:8}}>💤</div>
            <div style={{fontSize:17,fontWeight:700}}>No balance recorded yet</div>
            <div style={{fontSize:13.5,color:"#8c8479",marginTop:6,lineHeight:1.5}}>
              Send a balance to your Nudge bot on Telegram and it'll show up here.
            </div>
          </div>
          <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:8,color:"#b0a89d",fontSize:13,fontWeight:600,padding:"40px 0"}}>
            Nothing tracked yet · stay nudged
          </div>
        </>
      ) : (
        <>
          {/* Balance hero */}
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:22,padding:"20px 20px 18px"}}>
            <div style={{display:"flex",alignItems:"center",justifyContent:"space-between"}}>
              <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d"}}>Total balance</div>
              <button
                onClick={onCycleRecon}
                style={{display:"flex",alignItems:"center",gap:5,padding:"5px 10px",borderRadius:999,cursor:"pointer",background:r.bg,color:r.fg,fontSize:11.5,fontWeight:700,border:"none"}}
              >
                <span>{r.icon}</span><span>{r.label}</span>
              </button>
            </div>
            <div style={{fontSize:42,fontWeight:700,letterSpacing:-1.4,marginTop:8,fontFeatureSettings:"'tnum'"}}>{fmtINR(balance ?? 247830)}</div>
            <div style={{fontSize:12.5,color:"#a39a8e",marginTop:2}}>{balance != null ? "Last recorded from Telegram" : "Last recorded Today, 9:42 AM"}</div>
            <div style={{height:1,background:"#efe9df",margin:"14px 0 12px"}}/>
            <div style={{fontSize:12.5,color:"#8c8479"}}>{r.sub}</div>
          </div>

          {/* Two stats */}
          <div style={{display:"flex",gap:12,marginTop:12}}>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:"#b0a89d"}}>Spent · June</div>
              <div style={{fontSize:23,fontWeight:700,letterSpacing:-0.6,marginTop:8,fontFeatureSettings:"'tnum'"}}>{fmtINR(monthSpend)}</div>
            </div>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:"#b0a89d"}}>Savings rate</div>
              <div style={{fontSize:23,fontWeight:700,letterSpacing:-0.6,marginTop:8,color:savColor,fontFeatureSettings:"'tnum'"}}>{savRate}%</div>
            </div>
          </div>

          {/* Recent */}
          <div style={{display:"flex",alignItems:"baseline",justifyContent:"space-between",margin:"22px 2px 10px"}}>
            <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d"}}>Recent</div>
            <button onClick={onGoTransactions} style={{fontSize:12.5,fontWeight:700,color:"#c06a47",cursor:"pointer",background:"none",border:"none",padding:0}}>See all →</button>
          </div>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,overflow:"hidden"}}>
            {recent.map((t, i) => (
              <div key={i} style={{display:"flex",alignItems:"center",gap:12,padding:"13px 16px",borderTop:`1px solid ${t.sep}`}}>
                <div style={{width:36,height:36,borderRadius:10,background:"#f5f0e8",display:"flex",alignItems:"center",justifyContent:"center",fontSize:17,flexShrink:0}}>{t.emoji}</div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:14.5,fontWeight:600,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{t.merchant}</div>
                  <div style={{fontSize:12,color:"#a39a8e",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{t.sub}</div>
                </div>
                <div style={{fontSize:14.5,fontWeight:700,color:t.amountColor,fontFeatureSettings:"'tnum'",whiteSpace:"nowrap"}}>{t.amountText}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
