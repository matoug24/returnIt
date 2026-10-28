import AsyncStorage from "@react-native-async-storage/async-storage";

export type DriverCommand = {
  commandId: string;
  type: "accept_pickup" | "record_handoff" | "exception";
  packageId: string;
  expectedVersion: number;
  occurredAt: string;
  evidenceIds: string[];
  reason?: "customer_no_show"|"invalid_label"|"rejected_package"|"driver_delay"|"destination_closed"|"destination_rejected"|"lost"|"damaged";
  latitude?: number;
  longitude?: number;
};
const key = "returnet.driver.commands.v1";

export async function pendingCommands(): Promise<DriverCommand[]> {
  const value = await AsyncStorage.getItem(key);
  return value ? JSON.parse(value) as DriverCommand[] : [];
}

export async function enqueue(command: DriverCommand): Promise<void> {
  const current = await pendingCommands();
  if (!current.some(item => item.commandId === command.commandId)) {
    await AsyncStorage.setItem(key, JSON.stringify([...current, command]));
  }
}

export async function replay(send: (command: DriverCommand) => Promise<void>): Promise<{sent:number; conflict?:DriverCommand}> {
  const current = await pendingCommands(); let sent = 0;
  for (const command of current) {
    try { await send(command); sent += 1; await AsyncStorage.setItem(key, JSON.stringify(current.slice(sent))); }
    catch { return {sent, conflict: command}; }
  }
  return {sent};
}
