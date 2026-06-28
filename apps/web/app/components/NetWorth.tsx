"use client";
import { SNAPS } from "../lib/demoData";
import { fmtINR, fmtSigned } from "../lib/format";

interface Props { isEmpty: boolean; savRate: number; savColor: string; }

export default function NetWorth({ isEmpty, savRate, savColor }: Props) {
  const snaps = SNAPS;
  const vals = snaps.map(s => s.v);
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const W = 300, H = 110, pd = 10;
  const xAt = (i: number) => pd + i * ((W - 2 * pd) / (snaps.length - 1));
  const yAt = (v: number) => (H - pd) - ((v - mn) / ((mx - mn) || 1)) * (H - 2 * pd);
  let linePath = `M${xAt(0).toFixed(1)} ${yAt(vals[0]).toFixed(1)}`;
  for (let i = 1; i < snaps.length; i++) linePath += ` L${xAt(i).toFixed(1)} ${yAt(vals[i]).toFixed(1)}`;
  const areaPath = linePath + ` L${xAt(snaps.length-1).toFixed(1)} ${H} L${xAt(0).toFixed(1)} ${H} Z`;
  const last = snaps[snaps.length - 1].v, prev = snaps[snaps.length - 2].v;
  const delta = last - prev;
  const deltaPct = (delta / prev * 100).toFixed(1);
  const deltaColor = delta >= 0 ? "#5f8f6f" : "#b8503f";

  const nwRows = [...snaps].reverse().map((s, i) => {
    const idx = snaps.length - 1 - i;
    const pv = idx > 0 ? snaps[idx - 1].v : null;
    const dv = pv === null ? null : s.v - pv;
    return {
      label: s.m + " 2026",
      value: fmtINR(s.v),
      delta: dv === null ? "—" : fmtSigned(dv),
      deltaColor: dv === null ? "#c9c0b3" : dv >= 0 ? "#5f8f6f" : "#b8503f",
      sep: i === 0 ? "transparent" : "#f0ebe2",
    };
  });

  return (
    <div className="screen-enter">
      <div style={{fontSize:26,fontWeight:700,letterSpacing:-0.8,margin:"2px 2px 14px"}}>Net worth</div>

      {isEmpty ? (
        <>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:20}}>
            <div style={{fontSize:11.5,fontWeight:700,letterSpacing:"0.07em",textTransform:"uppercase",color:"#b0a89d"}}>Current balance</div>
            <div style={{fontSize:34,fontWeight:700,letterSpacing:-1,marginTop:6,fontFeatureSettings:"'tnum'"}}>{fmtINR(last)}</div>
          </div>
          <div style={{background:"#faf6ef",border:"1px dashed #ddd3c4",borderRadius:18,padding:22,textAlign:"center",marginTop:14}}>
            <div style={{fontSize:24,marginBottom:8}}>📈</div>
            <div style={{fontSize:15,fontWeight:700}}>Only one snapshot so far</div>
            <div style={{fontSize:13,color:"#8c8479",marginTop:6,lineHeight:1.5}}>We need at least two balance snapshots to chart your trend and savings delta. Check back next month.</div>
          </div>
        </>
      ) : (
        <>
          {/* Chart card */}
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:"18px 18px 14px"}}>
            <div style={{display:"flex",alignItems:"flex-end",justifyContent:"space-between"}}>
              <div>
                <div style={{fontSize:11.5,fontWeight:700,letterSpacing:"0.07em",textTransform:"uppercase",color:"#b0a89d"}}>Balance</div>
                <div style={{fontSize:30,fontWeight:700,letterSpacing:-1,marginTop:4,fontFeatureSettings:"'tnum'"}}>{fmtINR(last)}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:12,fontWeight:700,color:deltaColor,fontFeatureSettings:"'tnum'"}}>{fmtSigned(delta)}</div>
                <div style={{fontSize:11,color:"#a39a8e"}}>{Number(deltaPct) >= 0 ? "+" : ""}{deltaPct}% vs May</div>
              </div>
            </div>
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
            <div style={{display:"flex",justifyContent:"space-between",marginTop:6,fontSize:10.5,color:"#b0a89d",fontWeight:600}}>
              <span>Jul 2025</span><span>Jun 2026</span>
            </div>
          </div>

          {/* Stats */}
          <div style={{display:"flex",gap:12,marginTop:12}}>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.05em",textTransform:"uppercase",color:"#b0a89d"}}>Saved vs last period</div>
              <div style={{fontSize:21,fontWeight:700,letterSpacing:-0.4,marginTop:8,color:deltaColor,fontFeatureSettings:"'tnum'"}}>{fmtSigned(delta)}</div>
            </div>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,padding:"15px 16px"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.05em",textTransform:"uppercase",color:"#b0a89d"}}>Savings rate</div>
              <div style={{fontSize:21,fontWeight:700,letterSpacing:-0.4,marginTop:8,color:savColor,fontFeatureSettings:"'tnum'"}}>{savRate}%</div>
            </div>
          </div>

          {/* Snapshots */}
          <div style={{fontSize:12,fontWeight:700,letterSpacing:"0.09em",textTransform:"uppercase",color:"#b0a89d",margin:"22px 2px 10px"}}>Snapshots</div>
          <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:18,overflow:"hidden"}}>
            {nwRows.map((s, i) => (
              <div key={i} style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"12px 16px",borderTop:`1px solid ${s.sep}`}}>
                <span style={{fontSize:14,fontWeight:600,color:"#6f675c"}}>{s.label}</span>
                <div style={{display:"flex",alignItems:"center",gap:10}}>
                  <span style={{fontSize:11.5,fontWeight:700,color:s.deltaColor,fontFeatureSettings:"'tnum'"}}>{s.delta}</span>
                  <span style={{fontSize:14.5,fontWeight:700,fontFeatureSettings:"'tnum'"}}>{s.value}</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
