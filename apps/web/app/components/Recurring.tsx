"use client";
import { useState } from "react";
import { CATS, CatKey, RecurringItem } from "../lib/demoData";
import { fmtINR, ordinal } from "../lib/format";

interface Props {
  items: RecurringItem[];
  isEmpty: boolean;
  onUpdate: (items: RecurringItem[]) => void;
}

const BLANK: Omit<RecurringItem, "id"> = { name:"", amount:0, cat:"subscriptions", day:1, type:"debit", active:true };

export default function Recurring({ items, isEmpty, onUpdate }: Props) {
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<(Omit<RecurringItem,"id"> & { id: number|null }) | null>(null);
  const [formError, setFormError] = useState(false);

  const catOf = (key: string) => CATS.find(c => c.key === key) ?? { emoji:"📦", name:"Misc", cap:null };
  const rs = isEmpty ? [] : items;
  const outSum = rs.filter(r => r.active && r.type === "debit").reduce((a, r) => a + r.amount, 0);
  const inSum  = rs.filter(r => r.active && r.type === "credit").reduce((a, r) => a + r.amount, 0);

  const openAdd = () => { setForm({ id:null, ...BLANK }); setFormError(false); setModalOpen(true); };
  const openEdit = (r: RecurringItem) => { setForm({ ...r }); setFormError(false); setModalOpen(true); };
  const closeModal = () => { setModalOpen(false); setForm(null); setFormError(false); };
  const patchForm = (patch: Partial<typeof form>) => { if (form) setForm({ ...form, ...patch } as typeof form); };

  const onSave = () => {
    if (!form || !form.name?.trim() || !form.amount || form.amount <= 0) { setFormError(true); return; }
    const item: RecurringItem = { id: form.id ?? Date.now(), name: form.name.trim(), amount: Number(form.amount), cat: form.cat as CatKey, day: Math.max(1, Math.min(28, Number(form.day) || 1)), type: form.type, active: form.active };
    const next = form.id ? items.map(x => x.id === form.id ? item : x) : [...items, item];
    onUpdate(next);
    closeModal();
  };

  const ft = form?.type ?? "debit";

  return (
    <div className="screen-enter" style={{position:"relative"}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",margin:"2px 2px 14px"}}>
        <div style={{fontSize:26,fontWeight:700,letterSpacing:-0.8}}>Recurring</div>
        <button onClick={openAdd} style={{display:"flex",alignItems:"center",gap:5,background:"#c06a47",color:"#fff",fontSize:13,fontWeight:700,padding:"8px 14px",borderRadius:999,cursor:"pointer",border:"none"}}>
          <span style={{fontSize:15,lineHeight:1}}>+</span> New
        </button>
      </div>

      {rs.length === 0 ? (
        <div style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:20,padding:"34px 22px",textAlign:"center"}}>
          <div style={{fontSize:28,marginBottom:8}}>🔁</div>
          <div style={{fontSize:16,fontWeight:700}}>No recurring items yet</div>
          <div style={{fontSize:13,color:"#8c8479",marginTop:6,lineHeight:1.5}}>Add rent, salary, subscriptions and bills so Nudge can predict your month.</div>
          <button onClick={openAdd} style={{display:"inline-block",marginTop:16,background:"#c06a47",color:"#fff",fontSize:13,fontWeight:700,padding:"9px 18px",borderRadius:999,cursor:"pointer",border:"none"}}>Add your first</button>
        </div>
      ) : (
        <>
          <div style={{display:"flex",gap:12}}>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:16,padding:"13px 15px"}}>
              <div style={{fontSize:11,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.05em",color:"#b0a89d"}}>Out / month</div>
              <div style={{fontSize:19,fontWeight:700,color:"#b8503f",marginTop:6,fontFeatureSettings:"'tnum'"}}>{fmtINR(outSum)}</div>
            </div>
            <div style={{flex:1,background:"#fff",border:"1px solid #e9e3d9",borderRadius:16,padding:"13px 15px"}}>
              <div style={{fontSize:11,fontWeight:700,textTransform:"uppercase",letterSpacing:"0.05em",color:"#b0a89d"}}>In / month</div>
              <div style={{fontSize:19,fontWeight:700,color:"#5f8f6f",marginTop:6,fontFeatureSettings:"'tnum'"}}>{fmtINR(inSum)}</div>
            </div>
          </div>

          <div style={{display:"flex",flexDirection:"column",gap:10,marginTop:14}}>
            {rs.map(r => {
              const c = catOf(r.cat);
              return (
                <div key={r.id} style={{background:"#fff",border:"1px solid #e9e3d9",borderRadius:16,padding:"13px 15px",opacity:r.active ? 1 : 0.5}}>
                  <div style={{display:"flex",alignItems:"center",gap:12}}>
                    <div style={{width:38,height:38,borderRadius:11,background:"#f5f0e8",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,flexShrink:0}}>{c.emoji}</div>
                    <div style={{flex:1,minWidth:0}}>
                      <div style={{fontSize:15,fontWeight:700,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{r.name}</div>
                      <div style={{fontSize:12,color:"#a39a8e"}}>{c.name} · {ordinal(r.day)} of month</div>
                    </div>
                    <div style={{fontSize:15,fontWeight:700,color:r.type==="credit"?"#5f8f6f":"#26211c",fontFeatureSettings:"'tnum'"}}>
                      {r.type==="credit"?"+":"−"}{fmtINR(r.amount).replace("₹","₹")}
                    </div>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:8,marginTop:12,paddingTop:11,borderTop:"1px solid #f0ebe2"}}>
                    <button onClick={() => onUpdate(items.map(x => x.id===r.id ? {...x, active:!x.active} : x))}
                      style={{display:"flex",alignItems:"center",gap:7,cursor:"pointer",marginRight:"auto",background:"none",border:"none",padding:0}}>
                      <div style={{width:34,height:20,borderRadius:99,padding:2,background:r.active?"#c06a47":"#d8d0c4",transition:"background .15s"}}>
                        <div style={{width:16,height:16,borderRadius:"50%",background:"#fff",transform:`translateX(${r.active?"14px":"0px"})`,transition:"transform .15s",boxShadow:"0 1px 2px rgba(0,0,0,0.2)"}}/>
                      </div>
                      <span style={{fontSize:12,fontWeight:700,color:r.active?"#6f675c":"#b0a89d"}}>{r.active?"Active":"Paused"}</span>
                    </button>
                    <button onClick={() => openEdit(r)} style={{fontSize:12.5,fontWeight:700,color:"#6f675c",padding:"5px 12px",border:"1px solid #e6dfd4",borderRadius:8,cursor:"pointer",background:"none"}}>Edit</button>
                    <button onClick={() => onUpdate(items.filter(x => x.id !== r.id))} style={{fontSize:12.5,fontWeight:700,color:"#b8503f",padding:"5px 12px",border:"1px solid #ecd9d3",borderRadius:8,cursor:"pointer",background:"none"}}>Delete</button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Modal */}
      {modalOpen && form && (
        <div style={{position:"fixed",inset:0,zIndex:80,display:"flex",flexDirection:"column",justifyContent:"flex-end"}}>
          <div onClick={closeModal} style={{position:"absolute",inset:0,background:"rgba(38,33,28,0.32)",backdropFilter:"blur(2px)"}}/>
          <div style={{position:"relative",background:"#f5f2ec",borderRadius:"26px 26px 0 0",padding:"20px 20px 30px",maxHeight:"88%",overflowY:"auto",animation:"nudgeUp .25s ease both"}}>
            <div style={{width:38,height:4,borderRadius:99,background:"#d8d0c4",margin:"0 auto 16px"}}/>
            <div style={{fontSize:20,fontWeight:700,letterSpacing:-0.5,marginBottom:16}}>{form.id ? "Edit recurring" : "New recurring"}</div>
            <div style={{display:"flex",flexDirection:"column",gap:13}}>
              <div>
                <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:5}}>Name</div>
                <input value={form.name} onChange={e => patchForm({ name: e.target.value })} placeholder="e.g. Netflix"
                  style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:12,padding:"11px 13px",fontSize:14,fontFamily:"inherit"}}/>
              </div>
              <div style={{display:"flex",gap:11}}>
                <div style={{flex:1}}>
                  <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:5}}>Amount ₹</div>
                  <input type="number" value={form.amount || ""} onChange={e => patchForm({ amount: Number(e.target.value) })} placeholder="0"
                    style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:12,padding:"11px 13px",fontSize:14,fontFamily:"inherit",fontFeatureSettings:"'tnum'"}}/>
                </div>
                <div style={{flex:1}}>
                  <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:5}}>Day of month</div>
                  <input type="number" min={1} max={28} value={form.day} onChange={e => patchForm({ day: Number(e.target.value) })} placeholder="1"
                    style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:12,padding:"11px 13px",fontSize:14,fontFamily:"inherit",fontFeatureSettings:"'tnum'"}}/>
                </div>
              </div>
              <div>
                <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:5}}>Category</div>
                <select value={form.cat} onChange={e => patchForm({ cat: e.target.value as CatKey })}
                  style={{width:"100%",boxSizing:"border-box",border:"1px solid #e2dbd0",background:"#fff",borderRadius:12,padding:"11px 13px",fontSize:14,fontFamily:"inherit",fontWeight:600}}>
                  {CATS.map(c => <option key={c.key} value={c.key}>{c.emoji} {c.name}</option>)}
                </select>
              </div>
              <div>
                <div style={{fontSize:11,fontWeight:700,color:"#b0a89d",textTransform:"uppercase",letterSpacing:"0.05em",marginBottom:5}}>Type</div>
                <div style={{display:"flex",gap:8}}>
                  <button onClick={() => patchForm({ type:"debit" })}
                    style={{flex:1,textAlign:"center",padding:11,borderRadius:12,fontSize:13.5,fontWeight:700,cursor:"pointer",
                      border:`1.5px solid ${ft==="debit"?"#c06a47":"#e6dfd4"}`,
                      color: ft==="debit"?"#c06a47":"#8c8479",
                      background: ft==="debit"?"#f7ece5":"#fff"
                    }}>Debit (out)</button>
                  <button onClick={() => patchForm({ type:"credit" })}
                    style={{flex:1,textAlign:"center",padding:11,borderRadius:12,fontSize:13.5,fontWeight:700,cursor:"pointer",
                      border:`1.5px solid ${ft==="credit"?"#5f8f6f":"#e6dfd4"}`,
                      color: ft==="credit"?"#5f8f6f":"#8c8479",
                      background: ft==="credit"?"#e9f0ea":"#fff"
                    }}>Credit (in)</button>
                </div>
              </div>
              <button onClick={() => patchForm({ active: !form.active })}
                style={{display:"flex",alignItems:"center",justifyContent:"space-between",background:"#fff",border:"1px solid #e2dbd0",borderRadius:12,padding:"11px 13px",cursor:"pointer",width:"100%",textAlign:"left"}}>
                <span style={{fontSize:14,fontWeight:600}}>Active</span>
                <div style={{width:42,height:24,borderRadius:99,padding:2,background:form.active?"#5f8f6f":"#d8d0c4"}}>
                  <div style={{width:20,height:20,borderRadius:"50%",background:"#fff",transform:`translateX(${form.active?"18px":"0px"})`,transition:"transform .15s",boxShadow:"0 1px 2px rgba(0,0,0,0.2)"}}/>
                </div>
              </button>
            </div>
            {formError && <div style={{fontSize:12.5,color:"#b8503f",fontWeight:600,marginTop:10}}>Add a name and an amount first.</div>}
            <div style={{display:"flex",gap:11,marginTop:18}}>
              <button onClick={closeModal} style={{flex:1,textAlign:"center",fontSize:14,fontWeight:700,color:"#6f675c",padding:13,border:"1px solid #e6dfd4",borderRadius:13,cursor:"pointer",background:"none"}}>Cancel</button>
              <button onClick={onSave} style={{flex:2,textAlign:"center",fontSize:14,fontWeight:700,color:"#fff",background:"#c06a47",padding:13,borderRadius:13,cursor:"pointer",border:"none"}}>{form.id ? "Save changes" : "Add item"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
