import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { request } from "../api/client";
import AppRoutes from "../router";
import { signedInMeHandler, unauthorizedResponse } from "../test/handlers";
import { createTestQueryClient, renderWithProviders } from "../test/render";
import { server } from "../test/server";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./useAuth";

function ApiTrigger() {
  const { status } = useAuth();
  return (
    <button
      type="button"
      disabled={status !== "authenticated"}
      onClick={() => {
        request("GET", "/employees").catch(() => {});
      }}
    >
      Call API
    </button>
  );
}

describe("auth routing", () => {
  it("redirects a signed-out user from a protected route to login", async () => {
    renderWithProviders(
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>,
      { route: "/employees" },
    );

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("returns to login when any API call receives a 401", async () => {
    const user = userEvent.setup();
    server.use(signedInMeHandler(), http.get("/api/employees", unauthorizedResponse));

    renderWithProviders(
      <AuthProvider>
        <Routes>
          <Route path="/" element={<ApiTrigger />} />
          <Route path="/login" element={<div>Login page</div>} />
        </Routes>
      </AuthProvider>,
      { route: "/" },
    );

    const trigger = screen.getByRole("button", { name: "Call API" });
    await waitFor(() => expect(trigger).toBeEnabled());
    await user.click(trigger);

    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });

  it("logs out through the API, clears the query cache and returns to login", async () => {
    const user = userEvent.setup();
    let logoutCalls = 0;
    server.use(
      signedInMeHandler(),
      http.post("/api/auth/logout", () => {
        logoutCalls += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(["employees"], [{ id: 1 }]);

    renderWithProviders(
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>,
      { route: "/", queryClient },
    );

    expect(await screen.findByText("HR Manager")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /account menu/i }));
    await user.click(screen.getByRole("menuitem", { name: /logout/i }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(logoutCalls).toBe(1);
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
});
