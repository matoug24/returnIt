const values = new Map<string, string>();

const storage = {
  async getItem(key: string): Promise<string | null> {
    return values.get(key) ?? null;
  },
  async setItem(key: string, value: string): Promise<void> {
    values.set(key, value);
  },
  async clear(): Promise<void> {
    values.clear();
  }
};

export default storage;

