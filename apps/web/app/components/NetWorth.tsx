"use client";
import { fmtINR, dateShort } from "../lib/format";

interface Props {
  isEmpty: boolean;
  spendOverTime?: { date: string; amount: number }[];
}

export default function NetWorth({ isEmpty, spendOverTime }: Props) {
  const points = (spendOverTime ?? []).filter(p => p.amount > 0);
  const total = points.reduce((a, p) => a + p.amount, 0);
  const peak = points.reduce((m, p) => Math.max(m, p.amount), 0);
  const avg = points.length ? total / points.length : 0;

  return (
    <div className="screen-enter">
      <div style={{fontSize:26,fontWeight:700,letterSpacing:-0.8,margin:"2px 2px 14px"}}>Spending</div>

      {isEmpty || points.length < 2 ? (
        <div style={{background:"#faf6ef",border:"1px dashed #ddd3c4",borderRadius:18,padding:22,textAlign:"center"}}>
          <div style={{fontSize:24,marginBottom:8}}>📈</div>
          <div style={{fontSize:15,fontWeight:700}}>Not enough data yet</div>
          <div style={{fontSize:13,color:"#8c8479",marginTop:6,lineHeight:1.5}}>Log a few more expenses and your spending trend will chart here.</div>
        </div>
      ) : (
        <>
          {/* Chart card */}
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:"18px 18px 14px"}}>
            <div style={{fontSize:11.5,fontWeight:700,letterSpacing:"0.07em",textTransform:"uppercase",color:"#b0a89d"}}>Total spent</div>
            <div style={{fontSize:30,fontWeight:700,letterSpacing:-1,marginTop:4,fontFeatureSettings:"'tnum'"}}>{fmtINR(total)}</div>
            <Chart points={points} />
            <div style={{display:"flex",justifyContent:"space-between",marginTop:6,fontSize:10.5,color:"#b0a89d",fontWeight:600}}>
              <span>{dateShort(points[0].date)}</span><span>{dateShort(points[points.length - 1].date)}</span>
            </div>
          </div>

          {/* Stats */}
          <div style={{display:"flex",gap:12,marginTop:12}}>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.05em",textTransform:"uppercase",color:"#b0a89d"}}>Avg / day</div>
              <div style={{fontSize:21,fontWeight:700,letterSpacing:-0.4,marginTop:8,fontFeatureSettings:"'tnum'"}}>{fmtINR(avg)}</div>
            </div>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.05em",textTransform:"uppercase",color:"#b0a89d"}}>Highest day</div>
              <div style={{fontSize:21,fontWeight:700,letterSpacing:-0.4,marginTop:8,fontFeatureSettings:"'tnum'"}}>{fmtINR(peak)}</div>
            </div>
          </div>

          {/* Daily breakdown */}
          <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d",margin:"22px 2px 10px"}}>By day</div>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,overflow:"hidden"}}>
            {[...points].reverse().map((p, i) => (
              <div key={p.date} style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"12px 16px",borderTop:`1px solid ${i === 0 ? "transparent" : "#f0ebe2"}`}}>
                <span style={{fontSize:14,fontWeight:600,color:"#6f675c"}}>{dateShort(p.date)}</span>
                <span style={{fontSize:14.5,fontWeight:700,fontFeatureSettings:"'tnum'"}}>{fmtINR(p.amount)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Chart({ points }: { points: { date: string; amount: number }[] }) {
  const vals = points.map(p => p.amount);
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const W = 300, H = 110, pd = 10;
  const xAt = (i: number) => pd + i * ((W - 2 * pd) / (points.length - 1));
  const yAt = (v: number) => (H - pd) - ((v - mn) / ((mx - mn) || 1)) * (H - 2 * pd);
  let linePath = `M${xAt(0).toFixed(1)} ${yAt(vals[0]).toFixed(1)}`;
  for (let i = 1; i < points.length; i++) linePath += ` L${xAt(i).toFixed(1)} ${yAt(vals[i]).toFixed(1)}`;
  const areaPath = linePath + ` L${xAt(points.length - 1).toFixed(1)} ${H} L${xAt(0).toFixed(1)} ${H} Z`;
  return (
    <svg viewBox="0 0 300 110" preserveAspectRatio="none" style={{width:"100%",height:118,marginTop:14,overflow:"visible"}}>
      <defs>
        <linearGradient id="nwfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#c06a47" stopOpacity={0.18}/>
          <stop offset="100%" stopColor="#c06a47" stopOpacity={0}/>
        </linearGradient>
      </defs>
      <path d={areaPath} fill="url(#nwfill)"/>
      <path d={linePath} fill="none" stroke="#c06a47" strokeWidth={2.4} strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke"/>
    </svg>
  );
}
