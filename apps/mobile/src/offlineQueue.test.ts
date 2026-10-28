import AsyncStorage from "@react-native-async-storage/async-storage";
import { enqueue, pendingCommands, replay } from "./offlineQueue";

beforeEach(() => AsyncStorage.clear());
test("deduplicates and removes acknowledged commands", async () => { const command={commandId:"cmd-1",type:"accept_pickup" as const,packageId:"pkg",expectedVersion:1,occurredAt:new Date().toISOString(),evidenceIds:["e"]}; await enqueue(command); await enqueue(command); expect(await pendingCommands()).toHaveLength(1); expect(await replay(async()=>{})).toEqual({sent:1}); expect(await pendingCommands()).toHaveLength(0); });
test("stops on conflict and preserves the failed command", async () => { const command={commandId:"cmd-2",type:"record_handoff" as const,packageId:"pkg",expectedVersion:2,occurredAt:new Date().toISOString(),evidenceIds:["e"]}; await enqueue(command); const result=await replay(async()=>{throw new Error("409")}); expect(result.conflict?.commandId).toBe("cmd-2"); expect(await pendingCommands()).toHaveLength(1); });
