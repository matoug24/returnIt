export interface EvidenceProvider { capture(kind:"scan"|"photo"|"receipt"): Promise<{checksum:string; uri:string}>; }
export interface LocationProvider { activeSample(): Promise<{latitude:number;longitude:number;accuracy:number}|null>; }
export interface PushProvider { requestPermission(): Promise<boolean>; }

export const demoEvidence: EvidenceProvider = {
  async capture(kind) { return {checksum:`demo-${kind}-${Date.now()}`,uri:`demo://${kind}`}; }
};
export const demoLocation: LocationProvider = {
  async activeSample() { return {latitude:45.5017,longitude:-73.5673,accuracy:25}; }
};
export const demoPush: PushProvider = { async requestPermission() { return true; } };

