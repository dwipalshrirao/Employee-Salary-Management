import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { testEmployeeDetail } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import EmployeeFormPage from "./EmployeeFormPage";

function renderForm() {
  return renderWithProviders(
    <Routes>
      <Route path="/employees/new" element={<EmployeeFormPage />} />
      <Route path="/employees/:id" element={<div>Employee detail destination</div>} />
      <Route path="/employees" element={<div>Employees list</div>} />
    </Routes>,
    { route: "/employees/new" },
  );
}

async function choose(user, label, option) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(await screen.findByRole("option", { name: option }));
}

async function fillValidForm(user) {
  await user.type(await screen.findByLabelText("Full name"), "Asha Patel");
  await user.type(screen.getByLabelText("Email"), "asha.patel@acme.example");
  await choose(user, "Department", "Engineering");
  await choose(user, "Job title", "Software Engineer");
  await choose(user, "Country", "India");
  fireEvent.change(screen.getByLabelText("Hire date"), {
    target: { value: "2026-10-01" },
  });
  await user.type(screen.getByLabelText("Base salary"), "45000");
  await user.clear(screen.getByLabelText("Bonus"));
  await user.type(screen.getByLabelText("Bonus"), "4500");
  await user.clear(screen.getByLabelText("Allowances"));
  await user.type(screen.getByLabelText("Allowances"), "1800");
}

describe("EmployeeFormPage", () => {
  it("validates required fields and formats", async () => {
    const user = userEvent.setup();

    renderForm();
    await screen.findByLabelText("Full name");
    await user.click(screen.getByRole("button", { name: "Save employee" }));

    expect(await screen.findByText("Full name is required")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email")).toBeInTheDocument();
    expect(screen.getByText("Select a department")).toBeInTheDocument();
    expect(screen.getByText("Select a job title")).toBeInTheDocument();
    expect(screen.getByText("Select a country")).toBeInTheDocument();
    expect(screen.getByText("Hire date is required")).toBeInTheDocument();
    expect(screen.getByText("Base salary is required")).toBeInTheDocument();
  });

  it("shows the local-currency equivalent and submits cents", async () => {
    const user = userEvent.setup();
    let body;
    server.use(
      http.post("/api/employees", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(
          { ...testEmployeeDetail, id: 99, full_name: body.full_name, email: body.email },
          { status: 201 },
        );
      }),
    );

    renderForm();
    await fillValidForm(user);

    expect(
      await screen.findByText("Total: $51,300 (approximate: ₹4,257,900 INR)"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Save employee" }));

    expect(await screen.findByText("Employee detail destination")).toBeInTheDocument();
    expect(body).toMatchObject({
      full_name: "Asha Patel",
      email: "asha.patel@acme.example",
      department_id: 1,
      job_title_id: 1,
      country_code: "IN",
      hire_date: "2026-10-01",
      base_salary_cents: 4_500_000,
      bonus_cents: 450_000,
      allowances_cents: 180_000,
    });
    expect(body.manager_id).toBeUndefined();
  });

  it("maps a duplicate email conflict to the email field", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/employees", () =>
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

    renderForm();
    await fillValidForm(user);
    await user.click(screen.getByRole("button", { name: "Save employee" }));

    expect(await screen.findByText("Email already exists")).toBeInTheDocument();
  });

  it("prevents a second submit while the request is running", async () => {
    const user = userEvent.setup();
    let resolveRequest;
    let calls = 0;
    server.use(
      http.post("/api/employees", async () => {
        calls += 1;
        await new Promise((resolve) => {
          resolveRequest = resolve;
        });
        return HttpResponse.json({ ...testEmployeeDetail, id: 99 }, { status: 201 });
      }),
    );

    renderForm();
    await fillValidForm(user);
    const save = screen.getByRole("button", { name: "Save employee" });
    await user.click(save);

    await waitFor(() => expect(save).toBeDisabled());
    fireEvent.click(save);
    expect(calls).toBe(1);

    resolveRequest();
    expect(await screen.findByText("Employee detail destination")).toBeInTheDocument();
  });
});
