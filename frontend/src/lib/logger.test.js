import { afterEach, describe, expect, it, vi } from "vitest";

import { installGlobalErrorLogging, logUnexpectedError } from "./logger";

describe("frontend error logging", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("logs the stack and extra location details", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const error = new Error("boom");

    logUnexpectedError("window.error", error, {
      filename: "app.js",
      lineno: 12,
      colno: 4,
    });

    const [message, payload] = spy.mock.calls[0];
    expect(message).toBe("unexpected_frontend_error");
    expect(payload).toMatchObject({
      source: "window.error",
      name: "Error",
      message: "boom",
      filename: "app.js",
      lineno: 12,
      colno: 4,
    });
    expect(payload.stack).toContain("Error: boom");
  });

  it("installs and removes window error and rejection listeners", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const target = new EventTarget();
    const uninstall = installGlobalErrorLogging(target);

    target.dispatchEvent(
      Object.assign(new Event("error"), {
        error: new Error("window failed"),
        filename: "app.js",
        lineno: 2,
        colno: 3,
      }),
    );
    target.dispatchEvent(
      Object.assign(new Event("unhandledrejection"), {
        reason: new Error("promise failed"),
      }),
    );

    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[0][1]).toMatchObject({
      source: "window.error",
      message: "window failed",
      filename: "app.js",
      lineno: 2,
      colno: 3,
    });
    expect(spy.mock.calls[1][1]).toMatchObject({
      source: "unhandledrejection",
      message: "promise failed",
    });

    uninstall();
    target.dispatchEvent(
      Object.assign(new Event("error"), {
        error: new Error("ignored"),
      }),
    );
    expect(spy).toHaveBeenCalledTimes(2);
  });
});
