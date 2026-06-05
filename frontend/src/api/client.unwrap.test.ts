import { describe, it, expect } from "vitest";
import { unwrap } from "./client";

describe("unwrap", () => {
  it("extracts .data from a FastAPI ApiResponse envelope", () => {
    const env = { success: true, data: { hello: "world" }, message: null };
    expect(unwrap<{ hello: string }>(env)).toEqual({ hello: "world" });
  });

  it("returns bare payload unchanged when not an envelope", () => {
    const bare = { hello: "world" };
    expect(unwrap<{ hello: string }>(bare)).toEqual({ hello: "world" });
  });

  it("treats an object that merely has a 'data' key but no envelope marker as bare", () => {
    const bare = { data: [1, 2, 3] }; // no success/message → not an envelope
    expect(unwrap<{ data: number[] }>(bare)).toEqual({ data: [1, 2, 3] });
  });

  it("passes through null/primitive payloads", () => {
    expect(unwrap<null>(null as unknown)).toBeNull();
  });
});
