type Listener = (ev: MessageEvent) => void;

export class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  lastEventId = "";
  withCredentials = false;
  readyState = 0; // CONNECTING
  onmessage: Listener | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onopen: ((ev: Event) => void) | null = null;
  private listeners: Record<string, Listener[]> = {};
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: Listener) {
    (this.listeners[type] ||= []).push(fn);
  }
  removeEventListener(type: string, fn: Listener) {
    this.listeners[type] = (this.listeners[type] || []).filter((l) => l !== fn);
  }
  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }

  // ---- test helpers ----
  emit(data: unknown, opts: { id?: string } = {}) {
    if (opts.id) this.lastEventId = opts.id;
    const ev = new MessageEvent("message", {
      data: typeof data === "string" ? data : JSON.stringify(data),
      lastEventId: opts.id ?? this.lastEventId,
    });
    this.onmessage?.(ev);
    (this.listeners["message"] || []).forEach((l) => l(ev));
  }
  emitError() {
    const ev = new Event("error");
    this.onerror?.(ev);
    (this.listeners["error"] || []).forEach((l) => l(ev as MessageEvent));
  }

  static reset() {
    MockEventSource.instances = [];
  }
  static latest(): MockEventSource {
    return MockEventSource.instances[MockEventSource.instances.length - 1];
  }
}
