import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  testAnalyticsBaseSummary,
  testAnalyticsCountryBreakdown,
  testAnalyticsDepartmentBreakdown,
  testAnalyticsDistributionCountry,
  testAnalyticsDistributionDepartment,
  testAnalyticsJobTitleBreakdown,
  testAnalyticsOutliers,
  testAnalyticsSummary,
} from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import DashboardPage from "./DashboardPage";

const NativeResizeObserver = globalThis.ResizeObserver;

beforeEach(() => {
  globalThis.ResizeObserver = class ResizeObserver {
    constructor(callback) {
      this.callback = callback;
    }

    observe(target) {
      this.callback([{ target, contentRect: { width: 600, height: 300 } }]);
    }

    unobserve() {}

    disconnect() {}
  };
});

afterEach(() => {
  globalThis.ResizeObserver = NativeResizeObserver;
});

const EMPTY_SUMMARY = {
  headcount: 0,
  total_cents: 0,
  avg_cents: 0,
  min_cents: 0,
  max_cents: 0,
  components: { base_cents: 0, bonus_cents: 0, allowances_cents: 0 },
  country_count: 0,
  department_count: 0,
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>;
}

function renderDashboard(route = "/") {
  return renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/employees" element={<div>Employees destination</div>} />
      </Routes>
    </>,
    { route },
  );
}

function trackAnalyticsRequests() {
  const requests = [];
  server.use(
    http.get("/api/analytics/summary", ({ request }) => {
      const url = new URL(request.url);
      requests.push(url);
      return HttpResponse.json(
        url.searchParams.get("measure") === "base"
          ? testAnalyticsBaseSummary
          : testAnalyticsSummary,
      );
    }),
    http.get("/api/analytics/breakdown", ({ request }) => {
      const url = new URL(request.url);
      requests.push(url);
      const groupBy = url.searchParams.get("group_by");
      const measure = url.searchParams.get("measure") ?? "total";
      const countryCode = url.searchParams.get("country_code");
      if (groupBy === "job_title") {
        return HttpResponse.json({
          ...testAnalyticsJobTitleBreakdown,
          measure,
        });
      }
      if (groupBy === "department") {
        return HttpResponse.json({
          ...testAnalyticsDepartmentBreakdown,
          measure,
        });
      }
      return HttpResponse.json({
        ...testAnalyticsCountryBreakdown,
        measure,
        rows: countryCode
          ? testAnalyticsCountryBreakdown.rows.filter((row) => row.key === countryCode)
          : testAnalyticsCountryBreakdown.rows,
      });
    }),
    http.get("/api/analytics/distribution", ({ request }) => {
      const url = new URL(request.url);
      requests.push(url);
      const groupBy = url.searchParams.get("group_by");
      const measure = url.searchParams.get("measure") ?? "total";
      return HttpResponse.json({
        ...(groupBy === "country"
          ? testAnalyticsDistributionCountry
          : testAnalyticsDistributionDepartment),
        measure,
      });
    }),
    http.get("/api/analytics/outliers", ({ request }) => {
      const url = new URL(request.url);
      requests.push(url);
      const page = Number(url.searchParams.get("page") ?? "1");
      return HttpResponse.json({ ...testAnalyticsOutliers, page });
    }),
  );
  return requests;
}

describe("DashboardPage", () => {
  it("loads all dashboard widgets and formats the KPI values", async () => {
    const requests = trackAnalyticsRequests();

    renderDashboard();

    expect(await screen.findByText("Pay insights")).toBeInTheDocument();
    expect(screen.getByText("Active employees only")).toBeInTheDocument();
    expect(await screen.findByText("$812.3M")).toBeInTheDocument();
    expect(screen.getByText("9,700")).toBeInTheDocument();
    expect(screen.getByText("$83,740")).toBeInTheDocument();
    expect(screen.getAllByText("United States").length).toBeGreaterThan(0);
    expect(screen.getByText("$118,200 average")).toBeInTheDocument();
    expect(screen.getByText("Base")).toBeInTheDocument();
    expect(screen.getByText("82% · $666.1M")).toBeInTheDocument();
    expect(screen.getByText("11% · $89M")).toBeInTheDocument();
    expect(screen.getByText("7% · $57.2M")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Average compensation by country/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Average compensation by department/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Salary distribution by department/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Pay by job title")).toBeInTheDocument();
    expect(await screen.findByText("Engineering Manager")).toBeInTheDocument();
    expect(screen.getByText("$171,800")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pay outliers" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Paid more than 1.5x the average for the same job title and country (at least 5 peers)",
      ),
    ).toBeInTheDocument();
    const outlierRow = screen.getByRole("row", { name: /Marcus Vance/ });
    expect(within(outlierRow).getByRole("link", { name: "Marcus Vance" })).toHaveAttribute(
      "href",
      "/employees/9",
    );
    expect(within(outlierRow).getByText("$285,000")).toBeInTheDocument();
    expect(within(outlierRow).getByText("$150,000")).toBeInTheDocument();
    expect(within(outlierRow).getByText("1.9x")).toBeInTheDocument();

    await waitFor(() => expect(requests).toHaveLength(6));
    const summary = requests.filter((url) => url.pathname === "/api/analytics/summary");
    const breakdowns = requests.filter((url) => url.pathname === "/api/analytics/breakdown");
    const distributions = requests.filter((url) => url.pathname === "/api/analytics/distribution");
    const outliers = requests.filter((url) => url.pathname === "/api/analytics/outliers");
    expect(summary).toHaveLength(1);
    expect(breakdowns).toHaveLength(3);
    expect(distributions).toHaveLength(1);
    expect(outliers).toHaveLength(1);
    expect(summary[0].searchParams.get("measure")).toBe("total");
    expect(breakdowns.map((url) => url.searchParams.get("group_by")).sort()).toEqual([
      "country",
      "department",
      "job_title",
    ]);
    expect(distributions[0].searchParams.get("group_by")).toBe("department");
    expect(outliers[0].searchParams.get("page")).toBe("1");
    expect(outliers[0].searchParams.get("page_size")).toBe("25");
  });

  it("refetches every widget when the measure changes and writes the URL", async () => {
    const user = userEvent.setup();
    const requests = trackAnalyticsRequests();

    renderDashboard();
    await screen.findByText("$812.3M");
    await waitFor(() => expect(requests).toHaveLength(6));
    const initialCount = requests.length;

    await user.click(screen.getByRole("button", { name: "Base salary" }));

    expect(await screen.findByText("$666.1M")).toBeInTheDocument();
    expect(screen.getByText("$68,670")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(initialCount + 6));
    expect(
      requests.slice(initialCount).every((url) => url.searchParams.get("measure") === "base"),
    ).toBe(true);
    expect(screen.getByTestId("location")).toHaveTextContent("measure=base");
  });

  it("applies country and department filters to every widget", async () => {
    const user = userEvent.setup();
    const requests = trackAnalyticsRequests();

    renderDashboard();
    await screen.findByText("$812.3M");
    await waitFor(() => expect(requests).toHaveLength(6));
    const initialCount = requests.length;

    await user.click(screen.getByRole("combobox", { name: "Country" }));
    await user.click(await screen.findByRole("option", { name: "India" }));

    expect(await screen.findByText("$42,600 average")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(initialCount + 6));
    expect(
      requests.slice(initialCount).every((url) => url.searchParams.get("country_code") === "IN"),
    ).toBe(true);
    expect(screen.getByTestId("location")).toHaveTextContent("country_code=IN");
    const countryCount = requests.length;

    await user.click(screen.getByRole("combobox", { name: "Department" }));
    await user.click(await screen.findByRole("option", { name: "Engineering" }));

    await waitFor(() => expect(requests).toHaveLength(countryCount + 6));
    expect(
      requests.slice(countryCount).every((url) => url.searchParams.get("department_id") === "1"),
    ).toBe(true);
    expect(screen.getByTestId("location")).toHaveTextContent("department_id=1");
  });

  it("restores the measure and filters from the URL", async () => {
    const requests = trackAnalyticsRequests();

    renderDashboard("/?measure=base&country_code=IN&department_id=1");

    expect(await screen.findByText("$666.1M")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Base salary" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText("$42,600 average")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(6));
    for (const url of requests) {
      expect(url.searchParams.get("measure")).toBe("base");
      expect(url.searchParams.get("country_code")).toBe("IN");
      expect(url.searchParams.get("department_id")).toBe("1");
    }
  });

  it("shows empty states instead of NaN when there is no data", async () => {
    server.use(
      http.get("/api/analytics/summary", () => HttpResponse.json(EMPTY_SUMMARY)),
      http.get("/api/analytics/breakdown", ({ request }) => {
        const groupBy = new URL(request.url).searchParams.get("group_by");
        return HttpResponse.json({ group_by: groupBy, measure: "total", rows: [] });
      }),
      http.get("/api/analytics/distribution", () =>
        HttpResponse.json({
          measure: "total",
          bands: testAnalyticsDistributionDepartment.bands,
          groups: [],
        }),
      ),
      http.get("/api/analytics/outliers", () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 25 }),
      ),
    );

    renderDashboard();

    expect((await screen.findAllByText("$0")).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("No compensation data for these filters")).toBeInTheDocument();
    expect(screen.getAllByText("No data for these filters")).toHaveLength(2);
    expect(screen.getByText("No distribution data for these filters")).toBeInTheDocument();
    expect(screen.getByText("No job-title data for these filters")).toBeInTheDocument();
    expect(screen.getByText("No pay outliers for these filters")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("NaN");
  });

  it("switches the salary distribution between department and country", async () => {
    const user = userEvent.setup();
    const requests = trackAnalyticsRequests();

    renderDashboard();
    await screen.findByText("$812.3M");
    await waitFor(() => expect(requests).toHaveLength(6));
    const initialCount = requests.length;

    await user.click(screen.getByRole("button", { name: "By country" }));

    expect(
      await screen.findByRole("img", { name: /Salary distribution by country/ }),
    ).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(initialCount + 1));
    const distribution = requests
      .slice(initialCount)
      .find((url) => url.pathname === "/api/analytics/distribution");
    expect(distribution.searchParams.get("group_by")).toBe("country");
    expect(
      screen.getByRole("img", { name: /Salary distribution by country/ }),
    ).toHaveAccessibleName(/United States/);
  });

  it("sorts the job-title table on the client", async () => {
    const user = userEvent.setup();

    renderDashboard();
    expect(await screen.findByText("Engineering Manager")).toBeInTheDocument();
    const card = screen.getByRole("heading", { name: "Pay by job title" }).closest(".MuiCard-root");

    await user.click(within(card).getByText("Job title"));

    await waitFor(() => {
      const dataRows = within(card).getAllByRole("row").slice(1);
      expect(within(dataRows[0]).getByText("Account Executive")).toBeInTheDocument();
    });
  });

  it("paginates pay outliers on the server", async () => {
    const user = userEvent.setup();
    const requests = [];
    server.use(
      http.get("/api/analytics/outliers", ({ request }) => {
        const url = new URL(request.url);
        requests.push(url);
        return HttpResponse.json({
          ...testAnalyticsOutliers,
          total: 60,
          page: Number(url.searchParams.get("page") ?? "1"),
        });
      }),
    );

    renderDashboard();
    await screen.findByText("Marcus Vance");
    await waitFor(() => expect(requests).toHaveLength(1));
    const card = screen.getByRole("heading", { name: "Pay outliers" }).closest(".MuiCard-root");

    await user.click(within(card).getByRole("button", { name: /go to next page/i }));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("page")).toBe("2");
    expect(requests[1].searchParams.get("page_size")).toBe("25");
  });

  it("opens the employee list filtered by country from the country chart", async () => {
    const { container } = renderDashboard();
    await screen.findByText("$812.3M");

    const bars = container.querySelectorAll(".recharts-rectangle");
    expect(bars.length).toBeGreaterThan(0);
    fireEvent.click(bars[0]);

    expect(await screen.findByText("Employees destination")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/employees?country_code=US");
  });

  it("exposes a screen-reader alternative for chart selection", async () => {
    const user = userEvent.setup();

    renderDashboard();
    await screen.findByText("$812.3M");

    await user.click(screen.getByRole("button", { name: "United States: average $118,200" }));

    expect(await screen.findByText("Employees destination")).toBeInTheDocument();
  });

  it("shows an error state and retries every query", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get("/api/analytics/summary", () => {
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

    renderDashboard();

    expect(await screen.findByText("Could not load dashboard")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(calls).toBe(2));
  });
});
