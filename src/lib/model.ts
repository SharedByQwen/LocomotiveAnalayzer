import * as ort from "onnxruntime-web";
import type {ModelMetadata} from "../types";
import {diagnostics} from "./logger";
let sessionPromise:Promise<ort.InferenceSession>|null=null; let metadataPromise:Promise<ModelMetadata>|null=null;
export async function loadModel(){
 if(!sessionPromise){diagnostics.info("MODEL_LOAD_STARTED",{url:"/models/locomotive_model.onnx"});sessionPromise=ort.InferenceSession.create("/models/locomotive_model.onnx",{executionProviders:["wasm"],graphOptimizationLevel:"all"});}
 if(!metadataPromise){metadataPromise=fetch("/models/metadata.json").then(async r=>{if(!r.ok)throw new Error("Metadata request failed: HTTP "+r.status);return await r.json() as ModelMetadata;});}
 try{const [session,metadata]=await Promise.all([sessionPromise,metadataPromise]);diagnostics.info("MODEL_LOAD_SUCCEEDED",{inputs:session.inputNames,outputs:session.outputNames,version:metadata.model_version});return {session,metadata};}
 catch(e){sessionPromise=null;metadataPromise=null;diagnostics.error("MODEL_LOAD_FAILED",{error:e instanceof Error?e.message:String(e)});throw e;}
}
export async function predict(features:number[][]):Promise<number[]>{
 if(!features.length)return [];
 const {session,metadata}=await loadModel();
 if(metadata.features.length!==4)throw new Error("Model must declare exactly four features.");
 const input=session.inputNames[0], output=session.outputNames[0]; if(!input||!output)throw new Error("ONNX input/output name missing.");
 diagnostics.info("INFERENCE_STARTED",{records:features.length,input,output,featureOrder:metadata.features});
 const tensor=new ort.Tensor("float32",Float32Array.from(features.flat()),[features.length,4]);
 const result=await session.run({[input]:tensor}); const value=result[output];
 if(!value||!("data" in value))throw new Error("ONNX output tensor missing.");
 const values=Array.from(value.data as ArrayLike<number>,Number);
 if(values.length!==features.length||values.some(v=>!Number.isFinite(v)))throw new Error("ONNX returned invalid prediction values.");
 diagnostics.info("INFERENCE_SUCCEEDED",{count:values.length,min:Math.min(...values),max:Math.max(...values)});
 return values;
}