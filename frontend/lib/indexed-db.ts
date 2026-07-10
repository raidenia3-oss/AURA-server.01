"use client";

interface AMEData {
  id: string;
  name: string;
  status: string;
  lastSync?: string;
}

interface NewsArticle {
  url: string;
  title: string;
  content: string;
  timestamp: string;
}

class LocalDB {
  private db: IDBDatabase | null = null;
  private static instance: LocalDB;

  static getInstance(): LocalDB {
    if (!LocalDB.instance) {
      LocalDB.instance = new LocalDB();
    }
    return LocalDB.instance;
  }

  async init(): Promise<void> {
    if (this.db) return;
    return new Promise((resolve, reject) => {
      const request = indexedDB.open("ame-db", 2);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve();
      };

      request.onupgradeneeded = (e: IDBVersionChangeEvent) => {
        const db = (e.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains("ames")) {
          db.createObjectStore("ames", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("news")) {
          db.createObjectStore("news", { keyPath: "url" });
        }
        if (!db.objectStoreNames.contains("sync")) {
          db.createObjectStore("sync", { keyPath: "timestamp" });
        }
        if (!db.objectStoreNames.contains("chat")) {
          db.createObjectStore("chat", { keyPath: "id", autoIncrement: true });
        }
      };
    });
  }

  private async ensureInit(): Promise<void> {
    if (!this.db) await this.init();
  }

  async saveAME(ame: AMEData): Promise<void> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("ames", "readwrite");
    tx.objectStore("ames").put({ ...ame, lastSync: new Date().toISOString() });
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = reject;
    });
  }

  async getAME(id: string): Promise<AMEData | undefined> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("ames", "readonly");
    return new Promise((resolve, reject) => {
      const request = tx.objectStore("ames").get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = reject;
    });
  }

  async getAllAMEs(): Promise<AMEData[]> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("ames", "readonly");
    return new Promise((resolve, reject) => {
      const request = tx.objectStore("ames").getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = reject;
    });
  }

  async saveNews(article: NewsArticle): Promise<void> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("news", "readwrite");
    tx.objectStore("news").put(article);
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = reject;
    });
  }

  async getAllNews(): Promise<NewsArticle[]> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("news", "readonly");
    return new Promise((resolve, reject) => {
      const request = tx.objectStore("news").getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = reject;
    });
  }

  async saveChatMessage(msg: {
    role: string;
    text: string;
    ameId: string;
  }): Promise<void> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("chat", "readwrite");
    tx.objectStore("chat").put({
      ...msg,
      timestamp: new Date().toISOString(),
    });
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = reject;
    });
  }

  async getChatHistory(ameId: string): Promise<any[]> {
    await this.ensureInit();
    const tx = (this.db as IDBDatabase).transaction("chat", "readonly");
    return new Promise((resolve, reject) => {
      const request = tx.objectStore("chat").getAll();
      request.onsuccess = () => {
        const all = request.result || [];
        resolve(all.filter((m: any) => m.ameId === ameId));
      };
      request.onerror = reject;
    });
  }
}

export default LocalDB;
