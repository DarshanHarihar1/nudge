"use client";
import { useState } from "react";
import { CATS, Txn } from "../lib/demoData";
import { fmtINR, dateShort, isoDate, pad2 } from "../lib/format";

type RangeKey = "this" | "last" | "last3" | "custom";

interface Props { txns: Txn[]; isEmpty: boolean; }

function inRange(date: string, key: RangeKey, from: string, to: string): boolean {
  if (key === "this")   return date >= "2026-06-01" && date <= "2026-06-30";
  if (key === "last")   return date >= "2026-05-01" && date <= "2026-05-31";
  if (key === "last3")  return date >= "2026-04-01" && date <= "2026-06-30";
  if (key === "custom") return date >= from && date <= to;
  return true;
}

export default function Spending({ txns, isEmpty }: Props) {
  const [range, setRange] = useState<RangeKey>("this");
  const [from, setFrom] = useState("2026-06-01");
  const [to, setTo] = useState("2026-06-28");

  const spList = isEmpty ? [] : txns.filter(t => t.amount < 0 && inRange(t.date, range, from, to));
  const spTotal = spList.reduce((a, t) => a + Math.abs(t.amount), 0);

  const rangeLabels: Record<RangeKey, string> = { this:"This month", last:"Last month", last3:"Last 3 months", custom:"Custom range" };
  const tabs: [RangeKey, string][] = [["this","This month"],["last","Last month"],["last3","3 months"],["custom","Custom"]];

  // Category breakdown
  const spCats = CATS.map(c => {
    const total = spList.filter(t => t.cat === c.key).reduce((a, t) => a + Math.abs(t.amount), 0);
    return { c, total };
  }).filter(x => x.total > 0).sort((a, b) => b.total - a.total)
    .map(({ c, total }, i) => {
      const hasCap = !!c.cap && range !== "last3";
      const over = hasCap && total > (c.cap!);
      const pct = hasCap ? Math.min(100, Math.round(total / c.cap! * 100)) : 0;
      return {
        emoji: c.emoji, name: c.name,
        amountText: fmtINR(total),
        hasCap, pct: pct + "%",
        barColor: over ? "#b8503f" : "#c06a47",
        capText: over ? "over by " + fmtINR(total - c.cap!) : pct + "% of " + fmtINR(c.cap!),
        capColor: over ? "#b8503f" : "#a39a8e",
        sep: i === 0 ? "transparent" : "#f0ebe2",
      };
    });

  // Daily bars
  const spanStart = range === "this" ? "2026-06-01" : range === "last" ? "2026-05-01" : range === "last3" ? "2026-04-01" : from;
  const spanEnd   = range === "this" ? "2026-06-28" : range === "last" ? "2026-05-31" : range === "last3" ? "2026-06-28" : to;
  const dayMap: Record<string, number> = {};
  spList.forEach(t => { dayMap[t.date] = (dayMap[t.date] || 0) + Math.abs(t.amount); });
  const series: { date: string; v: number }[] = [];
  const ds = new Date(spanStart + "T00:00:00"), de = new Date(spanEnd + "T00:00:00");
  for (const d = new Date(ds); d <= de; d.setDate(d.getDate() + 1)) {
    const k = d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
    series.push({ date: k, v: dayMap[k] || 0 });
  }
  const maxV = Math.max(...series.map(s => s.v), 1);
  const bars = series.map(s => ({ h: Math.max(2, Math.round(s.v / maxV * 100)) + "%", color: s.v > 0 ? "#dcae9a" : "#efe9df" }));

  // Top merchants
  const mMap: Record<string, { sum: number; count: number }> = {};
  spList.forEach(t => { if (!mMap[t.merchant]) mMap[t.merchant] = { sum: 0, count: 0 }; mMap[t.merchant].sum += Math.abs(t.amount); mMap[t.merchant].count++; });
  const merchants = Object.entries(mMap).sort((a, b) => b[1].sum - a[1].sum).slice(0, 5)
    .map(([name, v], i) => ({ rank: i + 1, name, amountText: fmtINR(v.sum), count: v.count + (v.count === 1 ? " transaction" : " transactions"), sep: i === 0 ? "transparent" : "#f0ebe2" }));

  return (
    <div className="screen-enter">
      <div style={{fontSize:26,fontWeight:700,letterSpacing:-0.8,margin:"2px 2px 12px"}}>Spending</div>

      {/* Range tabs */}
      <div style={{display:"flex",gap:6,background:"#ece6dc",padding:3,borderRadius:12}}>
        {tabs.map(([key, label]) => (
          <button key={key} onClick={() => setRange(key)}
            style={{flex:1,textAlign:"center",padding:"8px 4px",borderRadius:9,fontSize:12,fontWeight:700,cursor:"pointer",border:"none",
              background: range === key ? "#fff" : "transparent",
              color: range === key ? "#26211c" : "#8c8479",
              boxShadow: range === key ? "0 1px 2px rgba(0,0,0,0.08)" : "none"
            }}>{label}</button>
        ))}
      </div>

      {range === "custom" && (
        <div style={{display:"flex",gap:10,marginTop:10}}>
          <div style={{flex:1}}>
            <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",marginBottom:4,textTransform:"uppercase",letterSpacing:"0.05em"}}>From</div>
            <input type="date" value={from} onChange={e => setFrom(e.target.value)}
              style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:11,padding:"9px 11px",fontSize:13,fontFamily:"inherit",color:"#26211c"}}/>
          </div>
          <div style={{flex:1}}>
            <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",marginBottom:4,textTransform:"uppercase",letterSpacing:"0.05em"}}>To</div>
            <input type="date" value={to} onChange={e => setTo(e.target.value)}
              style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:11,padding:"9px 11px",fontSize:13,fontFamily:"inherit",color:"#26211c"}}/>
          </div>
        </div>
      )}

      {isEmpty || spList.length === 0 ? (
        <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:"34px 22px",textAlign:"center",marginTop:14}}>
          <div style={{fontSize:28,marginBottom:8}}>🧾</div>
          <div style={{fontSize:16,fontWeight:700}}>No expenses in this period</div>
          <div style={{fontSize:13,color:"#8c8479",marginTop:6}}>Try a wider date range.</div>
        </div>
      ) : (
        <>
          {/* Total + bars */}
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:18,marginTop:14}}>
            <div style={{fontSize:11.5,fontWeight:700,letterSpacing:"0.07em",textTransform:"uppercase",color:"#b0a89d"}}>Total spend · {rangeLabels[range]}</div>
            <div style={{fontSize:32,fontWeight:700,letterSpacing:-1,marginTop:6,fontFeatureSettings:"'tnum'"}}>{fmtINR(spTotal)}</div>
            <div style={{display:"flex",alignItems:"flex-end",gap:3,height:84,marginTop:16}}>
              {bars.map((b, i) => (
                <div key={i} style={{flex:1,minWidth:0,background:b.color,height:b.h,borderRadius:"3px 3px 1px 1px"}}/>
              ))}
            </div>
            {series.length > 0 && (
              <div style={{display:"flex",justifyContent:"space-between",marginTop:8,fontSize:10.5,color:"#b0a89d",fontWeight:600}}>
                <span>{dateShort(series[0].date)}</span>
                <span>{dateShort(series[Math.floor(series.length/2)].date)}</span>
                <span>{dateShort(series[series.length-1].date)}</span>
              </div>
            )}
          </div>

          {/* Categories */}
          <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d",margin:"22px 2px 10px"}}>By category</div>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"6px 16px"}}>
            {spCats.map((c, i) => (
              <div key={i} style={{padding:"13px 0",borderTop:`1px solid ${c.sep}`}}>
                <div style={{display:"flex",alignItems:"center",gap:10}}>
                  <span style={{fontSize:17}}>{c.emoji}</span>
                  <span style={{flex:1,fontSize:14.5,fontWeight:600}}>{c.name}</span>
                  <span style={{fontSize:14.5,fontWeight:700,fontFeatureSettings:"'tnum'"}}>{c.amountText}</span>
                </div>
                {c.hasCap && (
                  <div style={{display:"flex",alignItems:"center",gap:8,marginTop:8}}>
                    <div style={{flex:1,height:6,background:"#f0ebe2",borderRadius:99,overflow:"hidden"}}>
                      <div style={{height:"100%",width:c.pct,background:c.barColor,borderRadius:99}}/>
                    </div>
                    <span style={{fontSize:11,color:c.capColor,fontWeight:600,whiteSpace:"nowrap"}}>{c.capText}</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Top merchants */}
          <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d",margin:"22px 2px 10px"}}>Top merchants</div>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,overflow:"hidden"}}>
            {merchants.map((m, i) => (
              <div key={i} style={{display:"flex",alignItems:"center",gap:12,padding:"13px 16px",borderTop:`1px solid ${m.sep}`}}>
                <div style={{width:24,fontSize:13,fontWeight:700,color:"#c9c0b3",fontFeatureSettings:"'tnum'"}}>{m.rank}</div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontSize:14.5,fontWeight:600}}>{m.name}</div>
                  <div style={{fontSize:12,color:"#a39a8e"}}>{m.count}</div>
                </div>
                <div style={{fontSize:14.5,fontWeight:700,fontFeatureSettings:"'tnum'"}}>{m.amountText}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
