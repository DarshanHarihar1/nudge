"use client";
import { CATS, Txn } from "../lib/demoData";
import { fmtINR, fmtSigned, dateShort } from "../lib/format";

interface Props {
  txns: Txn[];
  isEmpty: boolean;
  onGoTransactions: () => void;
}

export default function Overview({ txns, isEmpty, onGoTransactions }: Props) {
  const catOf = (key: string) => CATS.find(c => c.key === key) ?? { emoji:"📦", name:"Misc", cap:null };

  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const monthName = now.toLocaleString("en-US", { month: "long" });

  const monthSpends = txns.filter(t => t.date.startsWith(ym) && t.amount < 0);
  const monthSpend = monthSpends.reduce((a, t) => a + Math.abs(t.amount), 0);
  const txnCount = monthSpends.length;

  // Top spending category this month
  const catTotals = new Map<string, number>();
  for (const t of monthSpends) catTotals.set(t.cat, (catTotals.get(t.cat) ?? 0) + Math.abs(t.amount));
  const topEntry = [...catTotals.entries()].sort((a, b) => b[1] - a[1])[0];
  const topCat = topEntry ? catOf(topEntry[0]) : null;

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

  return (
    <div className="screen-enter">
      {isEmpty ? (
        <>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:22,padding:"28px 22px",textAlign:"center"}}>
            <div style={{fontSize:30,marginBottom:8}}>💤</div>
            <div style={{fontSize:17,fontWeight:700}}>No expenses yet</div>
            <div style={{fontSize:13.5,color:"#8c8479",marginTop:6,lineHeight:1.5}}>
              Send an expense to your Nudge bot on Telegram and it'll show up here.
            </div>
          </div>
          <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:8,color:"#b0a89d",fontSize:13,fontWeight:600,padding:"40px 0"}}>
            Nothing tracked yet · stay nudged
          </div>
        </>
      ) : (
        <>
          {/* Spend hero */}
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:22,padding:"20px 20px 18px"}}>
            <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d"}}>Spent this month</div>
            <div style={{fontSize:42,fontWeight:700,letterSpacing:-1.4,marginTop:8,fontFeatureSettings:"'tnum'"}}>{fmtINR(monthSpend)}</div>
            <div style={{fontSize:12.5,color:"#a39a8e",marginTop:2}}>{monthName} · {txnCount} expense{txnCount === 1 ? "" : "s"}</div>
          </div>

          {/* Two stats */}
          <div style={{display:"flex",gap:12,marginTop:12}}>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:"#b0a89d"}}>Transactions</div>
              <div style={{fontSize:23,fontWeight:700,letterSpacing:-0.6,marginTop:8,fontFeatureSettings:"'tnum'"}}>{txnCount}</div>
            </div>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.06em",textTransform:"uppercase",color:"#b0a89d"}}>Top category</div>
              <div style={{fontSize:18,fontWeight:700,letterSpacing:-0.4,marginTop:8,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>
                {topCat ? `${topCat.emoji} ${topCat.name}` : "—"}
              </div>
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
