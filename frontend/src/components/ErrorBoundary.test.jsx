import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/render";
import ErrorBoundary from "./ErrorBoundary";

function Bomb() {
  throw new Error("boom");
}

describe("ErrorBoundary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a fallback and logs the stack and component location", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderWithProviders(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    const call = spy.mock.calls.find(([message]) => message === "unexpected_frontend_error");
    expect(call).toBeTruthy();
    expect(call[1]).toMatchObject({
      source: "react-error-boundary",
      name: "Error",
      message: "boom",
    });
    expect(call[1].stack).toContain("Error: boom");
    expect(call[1].componentStack).toContain("Bomb");
  });
});
