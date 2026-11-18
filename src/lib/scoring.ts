import type { AnalysisRecord } from "../types";
export interface ScoredRecord {id:string;date:string;locomotiveNumber:string;prediction:number;weight:number;}
export function calculateWeightedScore(records:ScoredRecord[]):number{
 if(!records.length)throw new Error("Cannot calculate a score without predictions.");
 const sorted=[...records].sort((a,b)=>a.date.localeCompare(b.date));
 const numerator=sorted.reduce((sum,r,index)=>sum+(index+1)*r.prediction,0);
 return numerator/(sorted.length*(sorted.length+1)/2);
}
export function toScoredRecords(records:AnalysisRecord[]):ScoredRecord[]{
 return [...records].sort((a,b)=>a.date.localeCompare(b.date)).map((r,index)=>{
  if(typeof r.prediction!=="number"||!Number.isFinite(r.prediction))throw new Error("Missing prediction for record "+r.id);
  return {id:r.id,date:r.date,locomotiveNumber:r.locomotiveNumber,prediction:r.prediction,weight:index+1};
 });
}