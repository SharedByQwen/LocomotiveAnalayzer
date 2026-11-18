import type { DiagnosticEntry } from "../types";
const entries:DiagnosticEntry[]=[]; let activeRunId="app-startup"; const maxEntries=1200;
function newRunId(){return "run-"+new Date().toISOString().replace(/[-:.TZ]/g,"")+"-"+Math.random().toString(36).slice(2,7);}
export const diagnostics={
 startRun(){activeRunId=newRunId();this.info("ANALYSIS_RUN_STARTED");return activeRunId;},
 info(event:string,details?:Record<string,unknown>){this.write("INFO",event,details);},
 warn(event:string,details?:Record<string,unknown>){this.write("WARN",event,details);},
 error(event:string,details?:Record<string,unknown>){this.write("ERROR",event,details);},
 write(level:DiagnosticEntry["level"],event:string,details?:Record<string,unknown>){const entry:DiagnosticEntry={timestamp:new Date().toISOString(),level,event,runId:activeRunId,...(details?{details}:{})};entries.push(entry);if(entries.length>maxEntries)entries.splice(0,entries.length-maxEntries);const fn=level==="ERROR"?console.error:level==="WARN"?console.warn:console.info;fn("[LocomotiveAnalyzer]",JSON.stringify(entry));},
 export(){return JSON.stringify({application:"LocomotiveAnalayzer",exportedAt:new Date().toISOString(),userAgent:navigator.userAgent,entries},null,2);},
 count(){return entries.length;}
};