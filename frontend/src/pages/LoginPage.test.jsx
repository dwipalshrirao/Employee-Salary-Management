import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import { AuthProvider } from "../auth/AuthProvider";
import { useAuth } from "../auth/useAuth";
import { server } from "../test/server";
import { authResponse, signedInMeHandler } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import LoginPage from "./LoginPage";

function AuthProbe() {
  const { user, csrfToken } = useAuth();
  return (
    <div data-testid="auth-probe">
      {user?.email ?? "signed out"}:{csrfToken ?? "no-token"}
    </div>
  );
}

function renderLogin({ route = "/login", routeState } = {}) {
  return renderWithProviders(
    <AuthProvider>
      <AuthProbe />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Dashboard destination</h1>} />
        <Route path="/employees" element={<h1>Employees destination</h1>} />
      </Routes>
    </AuthProvider>,
    { route, routeState },
  );
}

async function signIn(user, password = "correct-password") {
  await user.type(await screen.findByLabelText(/^email$/i), "hr@acme.example");
  await user.type(screen.getByLabelText(/^password$/i), password);
  await user.click(screen.getByRole("button", { name: /^sign in$/i }));
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores auth in memory and redirects to the requested page", async () => {
    const user = userEvent.setup();

    renderLogin({ routeState: { from: "/employees" } });
    await signIn(user);

    expect(
      await screen.findByRole("heading", { name: "Employees destination" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("auth-probe")).toHaveTextContent("hr@acme.example:test-csrf-token");
    expect(localStorage.length).toBe(0);
  });

  it("shows the generic message for a 401", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          {
            error: {
              code: "unauthorized",
              message: "Invalid email or password",
              details: {},
            },
          },
          { status: 401 },
        ),
      ),
    );

    renderLogin();
    await signIn(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });

  it("shows the rate-limit message for a 429", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          {
            error: {
              code: "rate_limited",
              message: "Too many requests.",
              details: {},
            },
          },
          { status: 429 },
        ),
      ),
    );

    renderLogin();
    await signIn(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many attempts. Try again in a few minutes.",
    );
  });

  it("redirects an already signed-in user to the dashboard", async () => {
    server.use(signedInMeHandler());

    renderLogin();

    expect(
      await screen.findByRole("heading", { name: "Dashboard destination" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("auth-probe")).toHaveTextContent(
      `${authResponse.user.email}:${authResponse.csrf_token}`,
    );
  });
});
