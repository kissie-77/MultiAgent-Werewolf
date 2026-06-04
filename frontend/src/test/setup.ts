import "@testing-library/jest-dom/vitest";
import { beforeEach, vi } from "vitest";
import { MockEventSource } from "./MockEventSource";

// EventSource does not exist in jsdom; install the controllable double.
vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

beforeEach(() => {
  MockEventSource.reset();
  vi.restoreAllMocks();
  vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
});
