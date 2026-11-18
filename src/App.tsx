import {useMemo,useState} from "react";
import type {AnalysisRecord,ModelMetadata} from "./types";
import {diagnostics} from "./lib/logger";
import {loadModel,predict} from "./lib/model";
import {calculateWeightedScore,toScoredRecords} from "./lib/scoring";
const makeRecord=():AnalysisRecord=>({id:crypto.randomUUID(),date:new Date().toISOString().slice(0,10),locomotiveNumber:"1501",previousStatus:"1",daysSinceFailure:"7",repairHours:"5",repairCost:"10"});
export default function App(){
 const [records,setRecords]=useState<AnalysisRecord[]>([makeRecord()]);
 const [metadata,setMetadata]=useState<ModelMetadata|null>(null);
 const [status,setStatus]=useState<"unknown"|"loading"|"ready"|"error">("unknown");
 const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [score,setScore]=useState<number|null>(null); const [runId,setRunId]=useState("");
 const sorted=useMemo(()=>[...records].sort((a,b)=>a.date.localeCompare(b.date)),[records]);
 function update(id:string,key:keyof AnalysisRecord,value:string){setRecords(old=>old.map(r=>r.id===id?{...r,[key]:value,prediction:undefined}:r));setScore(null);}
 function add(){setRecords(old=>[...old,makeRecord()]);setScore(null);}
 function remove(id:string){setRecords(old=>old.length>1?old.filter(r=>r.id!==id):old);setScore(null);}
 async function checkModel(){setStatus("loading");setError("");try{const m=await loadModel();setMetadata(m.metadata);setStatus("ready");}catch(e){const msg=e instanceof Error?e.message:String(e);setError(msg);setStatus("error");diagnostics.error("MODEL_STATUS_ERROR",{message:msg});}}
 function validate():string|null{
  if(!records.length)return "حداقل یک رکورد لازم است.";
  for(const [i,r] of records.entries()){
   if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date))return "تاریخ رکورد "+(i+1)+" معتبر نیست.";
   if(!r.locomotiveNumber.trim())return "شماره لکوموتیو رکورد "+(i+1)+" خالی است.";
   const s=Number(r.previousStatus),d=Number(r.daysSinceFailure),h=Number(r.repairHours),c=Number(r.repairCost);
   if(s!==0&&s!==1)return "وضعیت سیر قبل فقط باید ۰ یا ۱ باشد.";
   if(![d,h,c].every(Number.isFinite)||d<0||h<0||c<0)return "مقادیر عددی باید معتبر و نامنفی باشند.";
  }return null;
 }
 async function analyze(){
  const invalid=validate();if(invalid){setError(invalid);diagnostics.warn("INPUT_VALIDATION_FAILED",{message:invalid});return;}
  setBusy(true);setError("");const id=diagnostics.startRun();setRunId(id);
  try{
   const ordered=[...records].sort((a,b)=>a.date.localeCompare(b.date));
   const features=ordered.map(r=>[Number(r.previousStatus),Number(r.daysSinceFailure),Number(r.repairHours),Number(r.repairCost)]);
   diagnostics.info("INPUT_VALIDATION_SUCCEEDED",{count:ordered.length,locomotives:[...new Set(ordered.map(r=>r.locomotiveNumber))],dates:ordered.map(r=>r.date),featureOrder:["previousStatus","daysSinceFailure","repairHours","repairCost"]});
   const predictions=await predict(features);const output=ordered.map((r,i)=>({...r,prediction:predictions[i]}));setRecords(output);
   const scored=toScoredRecords(output);const finalScore=calculateWeightedScore(scored);setScore(finalScore);
   diagnostics.info("WEIGHTED_SCORE_CALCULATED",{formula:"sum((index+1)*prediction)/sum(1..n)",rows:scored.map(({date,locomotiveNumber,prediction,weight})=>({date,locomotiveNumber,prediction,weight})),denominator:scored.length*(scored.length+1)/2,finalScore});
  }catch(e){const msg=e instanceof Error?e.message:String(e);setError(msg);diagnostics.error("ANALYSIS_FAILED",{message:msg,stack:e instanceof Error?e.stack:undefined});}
  finally{setBusy(false);}
 }
 function exportLogs(){const blob=new Blob([diagnostics.export()],{type:"application/json;charset=utf-8"});const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="locomotive-diagnostics-"+Date.now()+".json";a.click();URL.revokeObjectURL(url);diagnostics.info("DIAGNOSTICS_EXPORTED");}
 return <main className="shell">
  <header className="header"><div><div className="eyebrow">LOCAL ANALYSIS WORKSPACE</div><h1>تحلیلگر قابلیت سیر لکوموتیو</h1><p>ورود رکوردهای مستقل، پیش‌بینی مدل و محاسبه امتیاز نهایی</p></div><div className={"status "+status}>{status==="ready"?"مدل آماده است":status==="loading"?"در حال بارگذاری":status==="error"?"خطای مدل":"وضعیت مدل بررسی نشده"}</div></header>
  <section className="warning"><b>توجه:</b> راهنمای دیتاست فعلی آن را مصنوعی و تصادفی معرفی می‌کند؛ خروجی فعلی برای آزمایش فنی نرم‌افزار است و اعتبار عملیاتی ندارد.</section>
  <section className="panel model"><div><h2>وضعیت مدل</h2><p>{metadata?metadata.algorithm+" · نسخه "+metadata.model_version+" · "+(metadata.training_rows??"?")+" رکورد آموزشی":"مدل ONNX باید در پوشه public/models قرار داشته باشد."}</p>{metadata?.metrics&&<p>MAE {metadata.metrics.mae?.toFixed(4)} · RMSE {metadata.metrics.rmse?.toFixed(4)} · R² {metadata.metrics.r2?.toFixed(4)}</p>}</div><button className="secondary" onClick={checkModel} disabled={status==="loading"}>بررسی / بارگذاری مدل</button></section>
  <div className="section-title"><div><h2>رکوردهای تحلیل</h2><p>تاریخ فقط برای مرتب‌سازی است؛ شماره لکوموتیو فقط شناسه است. مدل فقط چهار ویژگی زیر را دریافت می‌کند.</p></div><button className="secondary" onClick={add}>＋ افزودن رکورد</button></div>
  <div className="records">{records.map((r,i)=><article className="record" key={r.id}><div className="record-title"><b>رکورد {i+1}</b>{r.prediction!==undefined&&<span className="chip">پیش‌بینی: {r.prediction.toFixed(5)}</span>}<button className="remove" onClick={()=>remove(r.id)} disabled={records.length===1}>×</button></div><div className="fields">
   <label>تاریخ<input type="date" value={r.date} onChange={e=>update(r.id,"date",e.target.value)}/></label>
   <label>شماره لکوموتیو<input value={r.locomotiveNumber} onChange={e=>update(r.id,"locomotiveNumber",e.target.value)}/></label>
   <label>وضعیت سیر قبل<select value={r.previousStatus} onChange={e=>update(r.id,"previousStatus",e.target.value)}><option value="1">۱ - سالم</option><option value="0">۰ - خراب</option></select></label>
   <label>روز از آخرین خرابی<input type="number" min="0" value={r.daysSinceFailure} onChange={e=>update(r.id,"daysSinceFailure",e.target.value)}/></label>
   <label>زمان تعمیرات امروز (ساعت)<input type="number" min="0" step="0.1" value={r.repairHours} onChange={e=>update(r.id,"repairHours",e.target.value)}/></label>
   <label>هزینه تعمیر (یورو)<input type="number" min="0" step="any" value={r.repairCost} onChange={e=>update(r.id,"repairCost",e.target.value)}/></label>
  </div></article>)}</div>
  <div className="actions"><span>وزن‌دهی پس از مرتب‌سازی تاریخ: {sorted.map((_,i)=>"وزن "+(i+1)).join(" ← ")}</span><button className="primary" onClick={analyze} disabled={busy}>{busy?"در حال تحلیل...":"اجرای تحلیل"}</button></div>
  {error&&<section className="error"><b>خطا</b><span>{error}</span><small>فایل لاگ تشخیصی را خروجی بگیر و ارسال کن.</small></section>}
  {score!==null&&<section className="panel result"><div><div className="eyebrow">FINAL WEIGHTED SCORE</div><h2>امتیاز نهایی قابلیت سیر</h2><p>میانگین وزن‌دار پیش‌بینی‌ها؛ جدیدترین رکورد بیشترین وزن را دارد.</p></div><strong className="score">{score.toFixed(6)}</strong><div className="table"><div className="row head"><span>تاریخ</span><span>شماره لکوموتیو</span><span>پیش‌بینی</span><span>وزن</span></div>{toScoredRecords(records).map(x=><div className="row" key={x.id}><span>{x.date}</span><span>{x.locomotiveNumber}</span><span>{x.prediction.toFixed(6)}</span><span>{x.weight}</span></div>)}</div><small>شناسه اجرا: {runId}</small></section>}
  <footer><div><b>عیب‌یابی</b><span>لاگ ساختاریافته در کنسول مرورگر ثبت می‌شود.</span></div><button className="secondary" onClick={exportLogs}>خروجی لاگ تشخیصی JSON · {diagnostics.count()}</button></footer>
 </main>;
}