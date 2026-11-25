import type {ModelMetadata} from "../types";
import {diagnostics} from "./logger";

type ModelStatus = {
  loaded:boolean;
  state?:"missing"|"loading"|"ready"|"error";
  error?:string|null;
  load_elapsed_seconds?:number|null;
  model_name?:string;
  model_version?:string;
  algorithm?:string;
  training_rows?:number;
  features?:string[];
  metrics?:ModelMetadata["metrics"];
  message?:string;
};

async function apiError(response:Response):Promise<Error>{
  let message = "HTTP " + response.status;
  try { const body = await response.json(); message = body.detail || message; } catch {}
  return new Error(message);
}

export async function loadModel():Promise<{metadata:ModelMetadata}>{
  const response = await fetch("/api/model/status");
  if(!response.ok) throw await apiError(response);
  const status = await response.json() as ModelStatus;
  if(!status.loaded){
    if(status.state === "loading") throw new Error("MODEL_LOADING");
    if(status.state === "error") throw new Error(status.error || "Model loading failed.");
    throw new Error(status.message || "No model is installed on the backend.");
  }
  const metadata:ModelMetadata = {
    model_name:status.model_name || "locomotive-capability-regressor",
    model_version:status.model_version || "unknown",
    algorithm:status.algorithm || "unknown",
    training_rows:status.training_rows,
    features:status.features || [],
    target:"",
    metrics:status.metrics
  };
  diagnostics.info("BACKEND_MODEL_READY",{version:metadata.model_version,algorithm:metadata.algorithm,loadSeconds:status.load_elapsed_seconds});
  return {metadata};
}

export async function uploadModelZip(file:File):Promise<void>{
  const form = new FormData();
  form.append("file",file);
  const response = await fetch("/api/model/upload",{method:"POST",body:form});
  if(!response.ok) throw await apiError(response);
  diagnostics.info("MODEL_ZIP_UPLOADED",{fileName:file.name,fileSize:file.size});
}

export async function predict(features:number[][]):Promise<number[]>{
  if(!features.length) return [];
  const response = await fetch("/api/predict",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({records:features})
  });
  if(!response.ok) throw await apiError(response);
  const result = await response.json() as {predictions:number[]};
  if(!Array.isArray(result.predictions)||result.predictions.length!==features.length||result.predictions.some(v=>!Number.isFinite(v))){
    throw new Error("Backend returned invalid prediction values.");
  }
  diagnostics.info("INFERENCE_SUCCEEDED",{count:result.predictions.length,min:Math.min(...result.predictions),max:Math.max(...result.predictions)});
  return result.predictions;
}
