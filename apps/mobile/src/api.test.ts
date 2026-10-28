import {request,sendCommand} from "./api";
import {text} from "./i18n";

beforeEach(()=>{(globalThis as {__DEV__?:boolean}).__DEV__=true;globalThis.fetch=jest.fn(async()=>({ok:true,json:async()=>({ok:true})})) as jest.Mock});

test("uses a development identity only in development",async()=>{await request("/v1/bookings",undefined,"customer@local.returnet.ca");expect(fetch).toHaveBeenCalledWith("http://localhost:8000/v1/bookings",expect.objectContaining({headers:expect.objectContaining({"X-Returnet-Dev-User":"customer@local.returnet.ca"})}))});

test("maps queued exception commands to the driver endpoint",async()=>{await sendCommand({commandId:"command-123",type:"exception",packageId:"package-1",expectedVersion:3,occurredAt:"2026-01-01T00:00:00Z",evidenceIds:[],reason:"customer_no_show"});expect(fetch).toHaveBeenCalledWith("http://localhost:8000/v1/driver/packages/package-1:exception",expect.objectContaining({method:"POST",body:expect.stringContaining("customer_no_show")}))});

test("keeps mobile English and French keys in parity",()=>{expect(Object.keys(text.en).sort()).toEqual(Object.keys(text.fr).sort())});
