import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { salaryHistoryHandler, testSalaryHistoryPage } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import HistoryPage from "./HistoryPage";

const BATCH_ID = "6f1c8a00-0000-0000-0000-000000000000";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>;
}

function renderHistory(route = "/history") {
  return renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/employees/:id" element={<div>Employee detail destination</div>} />
      </Routes>
    </>,
    { route },
  );
}

function trackHistoryRequests(overrides = {}) {
  const requests = [];
  server.use(
    http.get("/api/salary-history", ({ request }) => {
      requests.push(new URL(request.url));
      return HttpResponse.json({ ...testSalaryHistoryPage, ...overrides });
    }),
  );
  return requests;
}

describe("HistoryPage", () => {
  it("loads the default page once and renders the history table", async () => {
    const requests = trackHistoryRequests();

    renderHistory();

    expect(await screen.findByText("Asha Patel")).toBeInTheDocument();
    expect(screen.getByText("Salary history")).toBeInTheDocument();
    expect(screen.getByText("Every pay change across the organisation")).toBeInTheDocument();
    expect(screen.getByText("Base salary")).toBeInTheDocument();
    expect(screen.getByText("Bonus")).toBeInTheDocument();
    expect(screen.getByText("Allowances")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(1));

    const params = requests[0].searchParams;
    expect(params.get("sort_by")).toBe("effective_date");
    expect(params.get("sort_dir")).toBe("desc");
    expect(params.get("page")).toBe("1");
    expect(params.get("page_size")).toBe("25");
  });

  it("shows before and after values, percentages and dashes for unchanged components", async () => {
    renderHistory();

    expect(await screen.findByText("$42,857 → $45,000")).toBeInTheDocument();
    expect(screen.getByText("+5.0%")).toBeInTheDocument();
    expect(screen.getByText("$6,500 → $8,000")).toBeInTheDocument();
    expect(screen.getByText("+23.1%")).toBeInTheDocument();
    expect(screen.getByText("$115,000")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("debounces employee and reason search into one request per change", async () => {
    const user = userEvent.setup();
    const requests = trackHistoryRequests();

    renderHistory();
    await screen.findByText("Asha Patel");
    await user.type(screen.getByLabelText("Search employee"), "asha");

    await waitFor(() => expect(requests).toHaveLength(2), { timeout: 1500 });
    expect(requests[1].searchParams.get("employee")).toBe("asha");

    await user.type(screen.getByLabelText("Search reason"), "FY27");

    await waitFor(() => expect(requests).toHaveLength(3), { timeout: 1500 });
    expect(requests[2].searchParams.get("reason")).toBe("FY27");
  });

  it("resets to page 1 when a filter changes and writes the URL", async () => {
    const user = userEvent.setup();
    const requests = trackHistoryRequests({ total: 100 });

    renderHistory("/history?page=3&page_size=25&sort_by=effective_date&sort_dir=desc");
    await screen.findByText("Asha Patel");
    await user.click(screen.getByRole("combobox", { name: "Change type" }));
    await user.click(await screen.findByRole("option", { name: "Bulk update" }));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("change_type")).toBe("bulk_update");
    expect(requests[1].searchParams.get("page")).toBe("1");
    expect(screen.getByTestId("location")).toHaveTextContent("change_type=bulk_update");
    expect(screen.getByTestId("location")).not.toHaveTextContent("page=3");
  });

  it("sends inclusive date filters and resets the page", async () => {
    const requests = trackHistoryRequests({ total: 100 });

    renderHistory("/history?page=2");
    await screen.findByText("Asha Patel");
    fireEvent.change(screen.getByLabelText("From"), { target: { value: "2026-01-01" } });

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("date_from")).toBe("2026-01-01");
    expect(requests[1].searchParams.get("page")).toBe("1");

    fireEvent.change(screen.getByLabelText("To"), { target: { value: "2026-12-31" } });

    await waitFor(() => expect(requests).toHaveLength(3));
    expect(requests[2].searchParams.get("date_from")).toBe("2026-01-01");
    expect(requests[2].searchParams.get("date_to")).toBe("2026-12-31");
  });

  it("shows a removable batch chip from the URL", async () => {
    const requests = trackHistoryRequests();

    renderHistory(`/history?batch_id=${BATCH_ID}`);

    expect(await screen.findByText("Batch 6f1c8a")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0].searchParams.get("batch_id")).toBe(BATCH_ID);

    fireEvent.click(screen.getByTestId("CancelIcon"));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("batch_id")).toBeNull();
    expect(screen.queryByText("Batch 6f1c8a")).not.toBeInTheDocument();
    expect(screen.getByTestId("location")).not.toHaveTextContent("batch_id");
  });

  it("restores all filters from the URL", async () => {
    const requests = trackHistoryRequests();

    renderHistory(
      `/history?employee=asha&reason=FY27&change_type=bulk_update&date_from=2026-01-01&date_to=2026-12-31&batch_id=${BATCH_ID}&sort_by=employee&sort_dir=asc&page=2&page_size=50`,
    );

    await screen.findByText("Asha Patel");
    await waitFor(() => expect(requests).toHaveLength(1));
    const params = requests[0].searchParams;
    expect(params.get("employee")).toBe("asha");
    expect(params.get("reason")).toBe("FY27");
    expect(params.get("change_type")).toBe("bulk_update");
    expect(params.get("date_from")).toBe("2026-01-01");
    expect(params.get("date_to")).toBe("2026-12-31");
    expect(params.get("batch_id")).toBe(BATCH_ID);
    expect(params.get("sort_by")).toBe("employee");
    expect(params.get("sort_dir")).toBe("asc");
    expect(params.get("page")).toBe("2");
    expect(params.get("page_size")).toBe("50");

    expect(screen.getByLabelText("Search employee")).toHaveValue("asha");
    expect(screen.getByLabelText("Search reason")).toHaveValue("FY27");
  });

  it("sends server-side sorting and resets the page", async () => {
    const user = userEvent.setup();
    const requests = trackHistoryRequests({ total: 100 });

    renderHistory("/history?page=2&sort_by=effective_date&sort_dir=desc");
    await screen.findByText("Asha Patel");
    await user.click(screen.getByText("Date"));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("sort_by")).toBe("effective_date");
    expect(requests[1].searchParams.get("sort_dir")).toBe("asc");
    expect(requests[1].searchParams.get("page")).toBe("1");
  });

  it("links employees and opens detail when a row is clicked", async () => {
    const user = userEvent.setup();

    renderHistory();

    expect(await screen.findByRole("link", { name: "Asha Patel" })).toHaveAttribute(
      "href",
      "/employees/1",
    );

    await user.click(screen.getByText("FY27 raise"));

    expect(await screen.findByText("Employee detail destination")).toBeInTheDocument();
  });

  it("shows the empty state and clears every filter", async () => {
    const user = userEvent.setup();
    server.use(salaryHistoryHandler([], { total: 0 }));

    renderHistory(`/history?employee=asha&batch_id=${BATCH_ID}`);

    expect(await screen.findByText("No changes match your filters")).toBeInTheDocument();
    expect(screen.getByText("Batch 6f1c8a")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);

    expect(screen.getByTestId("location")).toHaveTextContent("/history");
    expect(screen.getByTestId("location")).not.toHaveTextContent("employee");
    expect(screen.queryByText("Batch 6f1c8a")).not.toBeInTheDocument();
  });

  it("shows an error state and retries", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get("/api/salary-history", () => {
        calls += 1;
        return HttpResponse.json(
          {
            error: {
              code: "internal_error",
              message: "Internal server error.",
              details: {},
            },
          },
          { status: 500 },
        );
      }),
    );

    renderHistory();

    expect(await screen.findByText("Could not load salary history")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(calls).toBe(2));
  });

  it("renders the loading state while the first page is requested", async () => {
    let release;
    const pending = new Promise((resolve) => {
      release = resolve;
    });
    server.use(
      http.get("/api/salary-history", async () => {
        await pending;
        return HttpResponse.json(testSalaryHistoryPage);
      }),
    );

    renderHistory();

    expect(await screen.findByRole("progressbar")).toBeInTheDocument();
    release();

    expect(await screen.findByText("Asha Patel")).toBeInTheDocument();
  });
});
