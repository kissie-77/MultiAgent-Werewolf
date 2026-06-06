import { describe, expect, it } from "vitest";
import { MockEventSource } from "./MockEventSource";

describe("test harness", () => {
  it("exposes EventSource as the mock", () => {
    const es = new EventSource("/x");
    expect(es).toBeInstanceOf(MockEventSource);
    expect(MockEventSource.latest().url).toBe("/x");
  });
});
