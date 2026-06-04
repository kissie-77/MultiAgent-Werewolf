import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";
import { MockEventSource } from "./MockEventSource";

// EventSource does not exist in jsdom; install the controllable double.
vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

// jsdom does not implement Element.prototype.scrollIntoView; stub it as a no-op
// so components that auto-scroll their log view can mount under test.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

beforeEach(() => {
  MockEventSource.reset();
  vi.restoreAllMocks();
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
});
