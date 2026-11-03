import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../test/server";
import { ApiError, request, setCsrfToken, setUnauthorizedHandler } from "./client";

describe("api client", () => {
  beforeEach(() => {
    setCsrfToken(null);
    setUnauthorizedHandler(null);
  });

  it("throws an ApiError with the standard error shape", async () => {
    server.use(
      http.get("/api/employees/1", () =>
        HttpResponse.json(
          {
            error: {
              code: "conflict",
              message: "Email already exists",
              details: { field: "email" },
            },
          },
          { status: 409 },
        ),
      ),
    );

    const error = await request("GET", "/employees/1").catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      code: "conflict",
      message: "Email already exists",
      details: { field: "email" },
    });
  });

  it("adds the CSRF token on writes", async () => {
    let capturedRequest;

    server.use(
      http.post("/api/employees", ({ request: incoming }) => {
        capturedRequest = incoming;
        return HttpResponse.json({ id: 1 }, { status: 201 });
      }),
    );

    setCsrfToken("csrf-123");

    await request("POST", "/employees", { body: { full_name: "Asha Rao" } });

    expect(capturedRequest.headers.get("x-csrf-token")).toBe("csrf-123");
    expect(await capturedRequest.json()).toEqual({ full_name: "Asha Rao" });
  });

  it("calls the signed-out handler on 401", async () => {
    const onUnauthorized = vi.fn();

    server.use(
      http.get("/api/employees", () =>
        HttpResponse.json(
          { error: { code: "unauthorized", message: "Not signed in", details: {} } },
          { status: 401 },
        ),
      ),
    );

    setUnauthorizedHandler(onUnauthorized);

    await expect(request("GET", "/employees")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not call the signed-out handler for a failed login", async () => {
    const onUnauthorized = vi.fn();

    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          { error: { code: "invalid_credentials", message: "Invalid credentials", details: {} } },
          { status: 401 },
        ),
      ),
    );

    setUnauthorizedHandler(onUnauthorized);

    await expect(
      request("POST", "/auth/login", { body: { email: "a@b.com", password: "bad" } }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
