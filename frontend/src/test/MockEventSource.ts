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
  // The real backend frames every event as a NAMED `event: game` SSE frame
  // (see sse_stream.format_sse). Per the EventSource/HTML spec, named events
  // are delivered ONLY to listeners registered via addEventListener(name, …);
  // `onmessage` fires only for default (unnamed) `message` frames. Model that
  // here so a store that subscribes via `onmessage` receives nothing.
  emit(data: unknown, opts: { id?: string; event?: string } = {}) {
    if (opts.id) this.lastEventId = opts.id;
    const eventName = opts.event ?? "game";
    const ev = new MessageEvent(eventName, {
      data: typeof data === "string" ? data : JSON.stringify(data),
      lastEventId: opts.id ?? this.lastEventId,
    });
    if (eventName === "message") this.onmessage?.(ev);
    (this.listeners[eventName] || []).forEach((l) => l(ev));
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
