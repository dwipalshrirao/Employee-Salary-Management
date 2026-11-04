import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { testBulkApply, testBulkPreview } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import BulkUpdatePage from "./BulkUpdatePage";

function renderBulkUpdate() {
  return renderWithProviders(
    <Routes>
      <Route path="/bulk-update" element={<BulkUpdatePage />} />
      <Route path="/employees" element={<div>Employees destination</div>} />
      <Route path="/history" element={<div>History destination</div>} />
    </Routes>,
    { route: "/bulk-update" },
  );
}

async function fillPercentTarget(user) {
  await user.type(await screen.findByLabelText("Adjustment value"), "5");
  await user.type(screen.getByLabelText("Reason"), "FY27 market adjustment");
  await user.click(screen.getByRole("checkbox", { name: /apply to all active employees/i }));
}

describe("BulkUpdatePage", () => {
  it("requires apply_to_all when no filter is selected and never applies before preview", async () => {
    const user = userEvent.setup();

    renderBulkUpdate();
    await user.type(await screen.findByLabelText("Adjustment value"), "5");
    await user.type(screen.getByLabelText("Reason"), "FY27 market adjustment");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(
      await screen.findByText(/choose a filter or apply to all active employees/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply to/i })).not.toBeInTheDocument();
  });

  it("previews a percentage update and displays the computed summary", async () => {
    const user = userEvent.setup();
    let body;
    server.use(
      http.post("/api/bulk-updates/preview", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(testBulkPreview);
      }),
    );

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText("Employees affected")).toBeInTheDocument();
    expect(screen.getByText("Asha Patel")).toBeInTheDocument();
    expect(screen.getByText("$85,000")).toBeInTheDocument();
    expect(screen.getByText("$89,250")).toBeInTheDocument();
    expect(body).toMatchObject({
      apply_to_all: true,
      component: "base",
      mode: "percent",
      percentage: "5",
    });
    expect(body).not.toHaveProperty("reason");
  });

  it("switches to fixed dollars and sends cents", async () => {
    const user = userEvent.setup();
    let body;
    server.use(
      http.post("/api/bulk-updates/preview", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          ...testBulkPreview,
          component: "allowances",
          mode: "fixed_amount",
        });
      }),
    );

    renderBulkUpdate();
    await user.click(await screen.findByRole("radio", { name: "Allowances" }));
    await user.click(screen.getByRole("radio", { name: "Add fixed amount" }));
    expect(
      screen.getByText("Annual amount in USD. For $100 per month, enter $1,200."),
    ).toBeInTheDocument();
    await user.type(screen.getByLabelText("Adjustment value"), "1200");
    await user.type(screen.getByLabelText("Reason"), "FY27 allowance");
    await user.click(screen.getByRole("checkbox", { name: /apply to all active employees/i }));
    await user.click(screen.getByRole("button", { name: "Preview" }));

    await waitFor(() => expect(body).toBeTruthy());
    expect(body).toMatchObject({
      component: "allowances",
      mode: "fixed_amount",
      amount_cents: 120_000,
      apply_to_all: true,
    });
  });

  it("requires confirmation and applies with the expected count", async () => {
    const user = userEvent.setup();
    let applyBody;
    server.use(
      http.post("/api/bulk-updates/apply", async ({ request }) => {
        applyBody = await request.json();
        return HttpResponse.json(testBulkApply);
      }),
    );

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(await screen.findByRole("button", { name: "Continue" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Apply this change?")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Apply to 2 employees" }));

    expect(await screen.findByText("Updated 2 employees")).toBeInTheDocument();
    expect(applyBody).toMatchObject({
      expected_count: 2,
      reason: "FY27 market adjustment",
      component: "base",
      mode: "percent",
      percentage: "5",
    });
    expect(await screen.findByRole("link", { name: "View changes in history" })).toHaveAttribute(
      "href",
      `/history?batch_id=${testBulkApply.batch_id}`,
    );
  });

  it("shows a result-too-large error on step 1 and closes the confirmation", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/bulk-updates/apply", () =>
        HttpResponse.json(
          {
            error: {
              code: "result_too_large",
              message: "This update would change too many records.",
              details: {},
            },
          },
          { status: 422 },
        ),
      ),
    );

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(await screen.findByRole("button", { name: "Continue" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Apply to 2 employees" }));

    expect(
      await screen.findByText("This update would change too many records."),
    ).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByLabelText("Adjustment value")).toHaveValue("5");
  });

  it("keeps the target values when going back from the preview", async () => {
    const user = userEvent.setup();

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(await screen.findByRole("button", { name: "Back" }));

    expect(screen.getByLabelText("Adjustment value")).toHaveValue("5");
    expect(screen.getByLabelText("Reason")).toHaveValue("FY27 market adjustment");
    expect(screen.getByRole("checkbox", { name: /apply to all active employees/i })).toBeChecked();
  });

  it("disables continue when no employees are affected", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("/api/bulk-updates/preview", () =>
        HttpResponse.json({ ...testBulkPreview, affected_count: 0, sample: [] }),
      ),
    );

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(await screen.findByText("No employees would change")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("returns to preview and refreshes it after a stale preview", async () => {
    const user = userEvent.setup();
    let previewCalls = 0;
    server.use(
      http.post("/api/bulk-updates/preview", () => {
        previewCalls += 1;
        return HttpResponse.json(testBulkPreview);
      }),
      http.post("/api/bulk-updates/apply", () =>
        HttpResponse.json(
          {
            error: {
              code: "stale_preview",
              message: "The data changed since the preview.",
              details: {},
            },
          },
          { status: 409 },
        ),
      ),
    );

    renderBulkUpdate();
    await fillPercentTarget(user);
    await user.click(screen.getByRole("button", { name: "Preview" }));
    await user.click(await screen.findByRole("button", { name: "Continue" }));
    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Apply to 2 employees" }));

    expect(await screen.findByText(/The data changed since the preview/)).toBeInTheDocument();
    await waitFor(() => expect(previewCalls).toBe(2));
  });
});
