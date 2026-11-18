import {describe,expect,it} from "vitest";
import {calculateWeightedScore} from "./scoring";
describe("calculateWeightedScore",()=>{
 it("sorts by date and weights newest record highest",()=>{
  const score=calculateWeightedScore([
   {id:"new",date:"2025-01-02",locomotiveNumber:"1501",prediction:0.8,weight:2},
   {id:"old",date:"2025-01-01",locomotiveNumber:"1501",prediction:0.2,weight:1}
  ]);
  expect(score).toBeCloseTo((0.2+1.6)/3,10);
 });
 it("uses linear weights 1..n",()=>{
  const score=calculateWeightedScore([
   {id:"1",date:"2025-01-01",locomotiveNumber:"1",prediction:0,weight:1},
   {id:"2",date:"2025-01-02",locomotiveNumber:"1",prediction:0,weight:2},
   {id:"3",date:"2025-01-03",locomotiveNumber:"1",prediction:1,weight:3}
  ]);
  expect(score).toBeCloseTo(0.5,10);
 });
 it("rejects an empty list",()=>expect(()=>calculateWeightedScore([])).toThrow());
});