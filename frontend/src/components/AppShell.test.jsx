import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../test/render";
import AppShell from "./AppShell";

function renderShell() {
  return renderWithProviders(
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<div>Dashboard content</div>} />
      </Route>
    </Routes>,
  );
}

describe("AppShell", () => {
  it("shows the primary navigation links", () => {
    renderShell();

    for (const name of ["Dashboard", "Employees", "History", "Bulk update"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("shows a user menu with logout", async () => {
    const user = userEvent.setup();

    renderShell();
    await user.click(screen.getByRole("button", { name: /account menu/i }));

    expect(screen.getByRole("menuitem", { name: /logout/i })).toBeInTheDocument();
  });
});
