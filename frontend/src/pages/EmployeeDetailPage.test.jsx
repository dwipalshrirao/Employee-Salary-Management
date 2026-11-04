import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { notFoundResponse, testDirectReports, testEmployeeDetail } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import EmployeeDetailPage from "./EmployeeDetailPage";

function renderDetail(route = "/employees/1") {
  return renderWithProviders(
    <Routes>
      <Route path="/employees/:id" element={<EmployeeDetailPage />} />
      <Route path="/employees" element={<div>Employees list</div>} />
      <Route path="/employees/:id/edit" element={<div>Edit employee</div>} />
    </Routes>,
    { route },
  );
}

describe("EmployeeDetailPage", () => {
  it("renders the profile, compensation and local-currency amounts", async () => {
    renderDetail();

    expect(await screen.findByRole("heading", { name: "Asha Patel" })).toBeInTheDocument();
    expect(screen.getByText("Software Engineer")).toBeInTheDocument();
    expect(screen.getByText("asha.patel@acme.example")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("India")).toBeInTheDocument();
    expect(screen.getByText("12 Apr 2021")).toBeInTheDocument();
    expect(screen.getAllByText("Ravi Shah").length).toBeGreaterThan(0);
    expect(screen.getByText("$45,000")).toBeInTheDocument();
    expect(screen.getByText("$4,500")).toBeInTheDocument();
    expect(screen.getByText("$1,800")).toBeInTheDocument();
    expect(screen.getByText("$51,300")).toBeInTheDocument();
    expect(screen.getByText(/Approximate: ₹4,257,900 INR/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Edit" })).toHaveAttribute("href", "/employees/1/edit");
  });

  it("keeps reporting and direct reports in separate sections", async () => {
    renderDetail();

    expect(await screen.findByRole("heading", { name: "Reporting" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Direct reports" })).toBeInTheDocument();
  });

  it("renders direct reports and the salary history timeline", async () => {
    renderDetail();

    expect(await screen.findByText("John Smith")).toBeInTheDocument();
    expect(screen.getByText("Account Executive")).toBeInTheDocument();
    expect(screen.getByText("Annual review")).toBeInTheDocument();
    expect(screen.getByText("Hire")).toBeInTheDocument();
    expect(screen.getByText(/base \$45,000 from \$40,000/)).toBeInTheDocument();
    expect(screen.getByText(/\(\+12.5%\)/)).toBeInTheDocument();
    expect(screen.getByText(/base \$40,000/)).toBeInTheDocument();
  });

  it("requests the next direct-reports page", async () => {
    const user = userEvent.setup();
    const pages = [];
    server.use(
      http.get("/api/employees/:id/direct-reports", ({ request }) => {
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") ?? "1");
        pages.push(page);
        return HttpResponse.json({
          ...testDirectReports,
          total: 30,
          page,
        });
      }),
    );

    renderDetail();
    await screen.findByText("John Smith");
    await user.click(screen.getByRole("button", { name: /go to next page/i }));

    await waitFor(() => expect(pages).toContain(2));
  });

  it("shows a not-found state with a link back to employees", async () => {
    server.use(
      http.get("/api/employees/:id", notFoundResponse),
      http.get("/api/employees/:id/history", notFoundResponse),
      http.get("/api/employees/:id/direct-reports", notFoundResponse),
    );

    renderDetail("/employees/999");

    expect(await screen.findByText("Employee not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to employees" })).toHaveAttribute(
      "href",
      "/employees",
    );
  });

  it("deactivates the employee through the confirmation dialog", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.post("/api/employees/:id/deactivate", () => {
        calls += 1;
        return HttpResponse.json({ ...testEmployeeDetail, status: "inactive" });
      }),
    );

    renderDetail();
    await screen.findByRole("heading", { name: "Asha Patel" });
    await user.click(screen.getByRole("button", { name: "Deactivate" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Deactivate employee?")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Deactivate" }));

    await waitFor(() => expect(calls).toBe(1));
    expect(await screen.findByRole("button", { name: "Reactivate" })).toBeInTheDocument();
  });

  it("keeps the deactivate dialog open on a 409", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/employees/:id/deactivate", () =>
        HttpResponse.json(
          {
            error: {
              code: "conflict",
              message: "This employee has 4 active direct reports. Reassign them first.",
              details: {},
            },
          },
          { status: 409 },
        ),
      ),
    );

    renderDetail();
    await screen.findByRole("heading", { name: "Asha Patel" });
    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Deactivate" }));

    expect(
      await within(dialog).findByText(
        "This employee has 4 active direct reports. Reassign them first.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("reactivates an inactive employee", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get("/api/employees/1", () =>
        HttpResponse.json({ ...testEmployeeDetail, status: "inactive" }),
      ),
      http.post("/api/employees/:id/reactivate", () => {
        calls += 1;
        return HttpResponse.json({ ...testEmployeeDetail, status: "active" });
      }),
    );

    renderDetail();
    await screen.findByRole("heading", { name: "Asha Patel" });
    await user.click(screen.getByRole("button", { name: "Reactivate" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Reactivate employee?")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Reactivate" }));

    expect(await screen.findByRole("button", { name: "Deactivate" })).toBeInTheDocument();
    expect(calls).toBe(1);
  });

  it("keeps the reactivate dialog open when the manager is inactive", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("/api/employees/1", () =>
        HttpResponse.json({ ...testEmployeeDetail, status: "inactive" }),
      ),
      http.post("/api/employees/:id/reactivate", () =>
        HttpResponse.json(
          {
            error: {
              code: "conflict",
              message: "Cannot reactivate while the manager is inactive.",
              details: {},
            },
          },
          { status: 409 },
        ),
      ),
    );

    renderDetail();
    await screen.findByRole("heading", { name: "Asha Patel" });
    await user.click(screen.getByRole("button", { name: "Reactivate" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Reactivate" }));

    expect(
      await within(dialog).findByText("Cannot reactivate while the manager is inactive."),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("cancels a status change without calling the API", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.post("/api/employees/:id/deactivate", () => {
        calls += 1;
        return HttpResponse.json({ ...testEmployeeDetail, status: "inactive" });
      }),
    );

    renderDetail();
    await screen.findByRole("heading", { name: "Asha Patel" });
    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls).toBe(0);
  });
});
