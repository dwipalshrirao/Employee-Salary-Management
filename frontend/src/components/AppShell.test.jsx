import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "../auth/AuthProvider";
import { signedInMeHandler } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import AppShell from "./AppShell";

function renderShell() {
  server.use(signedInMeHandler());

  return renderWithProviders(
    <AuthProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<div>Dashboard content</div>} />
        </Route>
      </Routes>
    </AuthProvider>,
  );
}

describe("AppShell", () => {
  it("shows the primary navigation links", () => {
    renderShell();

    for (const name of ["Dashboard", "Employees", "History", "Bulk update"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("shows the signed-in user and a logout menu item", async () => {
    const user = userEvent.setup();

    renderShell();
    expect(await screen.findByText("HR Manager")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /account menu/i }));

    expect(screen.getByRole("menuitem", { name: /logout/i })).toBeInTheDocument();
  });
});
