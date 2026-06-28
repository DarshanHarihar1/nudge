"use client";
import { useState } from "react";
import { CATS, CatKey, Txn } from "../lib/demoData";
import { fmtSigned, dateShort } from "../lib/format";

interface Props { txns: Txn[]; isEmpty: boolean; onUpdateTxns: (txns: Txn[]) => void; }

type RangeKey = "all" | "this" | "last" | "last3";

function inRange(date: string, key: RangeKey): boolean {
  if (key === "this")  return date >= "2026-06-01" && date <= "2026-06-30";
  if (key === "last")  return date >= "2026-05-01" && date <= "2026-05-31";
  if (key === "last3") return date >= "2026-04-01" && date <= "2026-06-30";
  return true;
}

function badgeFor(src: Txn["source"]) {
  if (src === "recurring") return { badge:"🔄 AUTO", bg:"#ece6f3", fg:"#6a5891" };
  if (src === "telegram")  return { badge:"TELEGRAM", bg:"#e2edf3", fg:"#3f7194" };
  return { badge:"MANUAL", bg:"#efeae1", fg:"#8c8479" };
}

const PAGE_SIZE = 25;

export default function Transactions({ txns, isEmpty, onUpdateTxns }: Props) {
  const [search, setSearch] = useState("");
  const [filterCat, setFilterCat] = useState<string>("all");
  const [filterRange, setFilterRange] = useState<RangeKey>("all");
  const [page, setPage] = useState(1);
  const [editId, setEditId] = useState<number | null>(null);
  const [draft, setDraft] = useState<{ amount: string; date: string; cat: CatKey; note: string; sign: number } | null>(null);

  const filtered = isEmpty ? [] : txns.filter(t => {
    if (filterCat !== "all" && t.cat !== filterCat) return false;
    if (!inRange(t.date, filterRange)) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      if (!(t.merchant.toLowerCase().includes(q) || (t.note || "").toLowerCase().includes(q))) return false;
    }
    return true;
  });

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const p = Math.min(page, pageCount);
  const pageRows = filtered.slice((p - 1) * PAGE_SIZE, p * PAGE_SIZE);
  const catOf = (key: string) => CATS.find(c => c.key === key) ?? { emoji:"📦", name:"Misc", cap:null };
  const catOptions = [{ key:"all", label:"All categories" }, ...CATS.map(c => ({ key:c.key, label:`${c.emoji} ${c.name}` }))];
  const rangeOptions = [{ key:"all", label:"All time" }, { key:"this", label:"This month" }, { key:"last", label:"Last month" }, { key:"last3", label:"Last 3 months" }];

  const startEdit = (t: Txn) => {
    if (t.source === "recurring") return;
    setEditId(t.id);
    setDraft({ amount: String(Math.abs(t.amount)), date: t.date, cat: t.cat, note: t.note || "", sign: t.amount < 0 ? -1 : 1 });
  };
  const cancelEdit = () => { setEditId(null); setDraft(null); };
  const saveEdit = () => {
    if (!draft) return;
    onUpdateTxns(txns.map(t => t.id === editId ? { ...t, amount: draft.sign * Math.abs(Number(draft.amount) || 0), date: draft.date, cat: draft.cat, note: draft.note } : t));
    cancelEdit();
  };

  return (
    <div className="screen-enter">
      <div style={{fontSize:26,fontWeight:700,letterSpacing:-0.8,margin:"2px 2px 12px"}}>Transactions</div>

      {/* Search */}
      <div style={{position:"relative",marginBottom:8}}>
        <span style={{position:"absolute",left:13,top:"50%",transform:"translateY(-50%)",fontSize:14,color:"#b0a89d"}}>⌕</span>
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search merchant or note"
          style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:12,padding:"11px 12px 11px 32px",fontSize:13.5,fontFamily:"inherit",color:"#26211c"}}/>
      </div>
      <div style={{display:"flex",gap:8}}>
        <select value={filterCat} onChange={e => { setFilterCat(e.target.value); setPage(1); }}
          style={{flex:1,minWidth:0,border:"1px solid #e2dbd0",background:"#fff",borderRadius:11,padding:"9px 10px",fontSize:12.5,fontFamily:"inherit",color:"#26211c",fontWeight:600}}>
          {catOptions.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
        <select value={filterRange} onChange={e => { setFilterRange(e.target.value as RangeKey); setPage(1); }}
          style={{flex:1,minWidth:0,border:"1px solid #e2dbd0",background:"#fff",borderRadius:11,padding:"9px 10px",fontSize:12.5,fontFamily:"inherit",color:"#26211c",fontWeight:600}}>
          {rangeOptions.map(o => <option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:"34px 22px",textAlign:"center",marginTop:14}}>
          <div style={{fontSize:28,marginBottom:8}}>🔍</div>
          <div style={{fontSize:16,fontWeight:700}}>No transactions match</div>
          <div style={{fontSize:13,color:"#8c8479",marginTop:6}}>Clear a filter or widen the date range.</div>
        </div>
      ) : (
        <>
          <div style={{fontSize:11.5,color:"#a39a8e",fontWeight:600,margin:"12px 2px 8px"}}>
            {(p-1)*PAGE_SIZE+1}–{Math.min(p*PAGE_SIZE,filtered.length)} of {filtered.length}
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:8}}>
            {pageRows.map(t => {
              const c = catOf(t.cat);
              const b = badgeFor(t.source);
              const isRec = t.source === "recurring";
              const editing = editId === t.id;
              return (
                <div key={t.id} style={{background:"#fff",border:`1px solid ${editing?"#c06a47":"#e9e3d9"}`,borderRadius:14,padding:"12px 14px"}}>
                  <div onClick={() => startEdit(t)} style={{display:"flex",alignItems:"center",gap:11,cursor:isRec?"default":"pointer"}}>
                    <div style={{width:34,height:34,borderRadius:10,background:"#f5f0e8",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,flexShrink:0}}>{c.emoji}</div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{display:"flex",alignItems:"center",gap:6}}>
                        <span style={{fontSize:14,fontWeight:700,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{t.merchant}</span>
                        <span style={{fontSize:9.5,fontWeight:800,letterSpacing:"0.04em",padding:"2px 6px",borderRadius:6,flexShrink:0,background:b.bg,color:b.fg}}>{b.badge}</span>
                      </div>
                      <div style={{fontSize:12,color:"#a39a8e",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>
                        {c.name}{t.note ? " · " + t.note : ""}
                      </div>
                    </div>
                    <div style={{textAlign:"right",flexShrink:0}}>
                      <div style={{fontSize:14.5,fontWeight:700,color:t.amount<0?"#26211c":"#5f8f6f",fontFeatureSettings:"'tnum'"}}>{fmtSigned(t.amount)}</div>
                      <div style={{fontSize:11,color:"#bcb3a6"}}>{dateShort(t.date)}</div>
                    </div>
                  </div>

                  {editing && draft && (
                    <div style={{marginTop:12,paddingTop:12,borderTop:"1px solid #f0ebe2",display:"flex",flexDirection:"column",gap:9}}>
                      <div style={{display:"flex",gap:9}}>
                        <div style={{flex:1}}>
                          <div style={{fontSize:10.5,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:4}}>Amount ₹</div>
                          <input type="number" value={draft.amount} onChange={e => setDraft(d => d ? {...d, amount:e.target.value} : d)}
                            style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",borderRadius:9,padding:"8px 10px",fontSize:13,fontFamily:"inherit",fontFeatureSettings:"'tnum'"}}/>
                        </div>
                        <div style={{flex:1}}>
                          <div style={{fontSize:10.5,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:4}}>Date</div>
                          <input type="date" value={draft.date} onChange={e => setDraft(d => d ? {...d, date:e.target.value} : d)}
                            style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",borderRadius:9,padding:"8px 10px",fontSize:13,fontFamily:"inherit"}}/>
                        </div>
                      </div>
                      <div>
                        <div style={{fontSize:10.5,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:4}}>Category</div>
                        <select value={draft.cat} onChange={e => setDraft(d => d ? {...d, cat:e.target.value as CatKey} : d)}
                          style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",borderRadius:9,padding:"8px 10px",fontSize:13,fontFamily:"inherit",fontWeight:600}}>
                          {CATS.map(c => <option key={c.key} value={c.key}>{c.emoji} {c.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <div style={{fontSize:10.5,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:4}}>Note</div>
                        <input value={draft.note} onChange={e => setDraft(d => d ? {...d, note:e.target.value} : d)} placeholder="Add a note"
                          style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",borderRadius:9,padding:"8px 10px",fontSize:13,fontFamily:"inherit"}}/>
                      </div>
                      <div style={{display:"flex",gap:9,marginTop:2}}>
                        <button onClick={cancelEdit} style={{flex:1,textAlign:"center",fontSize:13,fontWeight:700,color:"#6f675c",padding:9,border:"1px solid #e6dfd4",borderRadius:10,cursor:"pointer",background:"none"}}>Cancel</button>
                        <button onClick={saveEdit} style={{flex:1,textAlign:"center",fontSize:13,fontWeight:700,color:"#fff",background:"#c06a47",padding:9,borderRadius:10,cursor:"pointer",border:"none"}}>Save</button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginTop:16}}>
            <button onClick={() => setPage(q => Math.max(1, q-1))} disabled={p <= 1}
              style={{fontSize:13,fontWeight:700,padding:"8px 14px",borderRadius:10,cursor:p<=1?"default":"pointer",border:"1px solid #e6dfd4",color:p<=1?"#cfc6b9":"#26211c",background:p<=1?"#f3efe8":"#fff"}}>← Prev</button>
            <div style={{fontSize:12,fontWeight:700,color:"#a39a8e"}}>Page {p} / {pageCount}</div>
            <button onClick={() => setPage(q => Math.min(pageCount, q+1))} disabled={p >= pageCount}
              style={{fontSize:13,fontWeight:700,padding:"8px 14px",borderRadius:10,cursor:p>=pageCount?"default":"pointer",border:"1px solid #e6dfd4",color:p>=pageCount?"#cfc6b9":"#26211c",background:p>=pageCount?"#f3efe8":"#fff"}}>Next →</button>
          </div>
        </>
      )}
    </div>
  );
}
