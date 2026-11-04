import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  testAnalyticsBaseSummary,
  testAnalyticsCountryBreakdown,
  testAnalyticsDepartmentBreakdown,
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
  );
  return requests;
}

describe("DashboardPage", () => {
  it("loads the three analytics widgets and formats the KPI values", async () => {
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
    expect(screen.getByText("11% · $89.0M")).toBeInTheDocument();
    expect(screen.getByText("7% · $57.2M")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Average compensation by country/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /Average compensation by department/ }),
    ).toBeInTheDocument();

    await waitFor(() => expect(requests).toHaveLength(3));
    const summary = requests.filter((url) => url.pathname === "/api/analytics/summary");
    const breakdowns = requests.filter((url) => url.pathname === "/api/analytics/breakdown");
    expect(summary).toHaveLength(1);
    expect(breakdowns).toHaveLength(2);
    expect(summary[0].searchParams.get("measure")).toBe("total");
    expect(breakdowns.map((url) => url.searchParams.get("group_by")).sort()).toEqual([
      "country",
      "department",
    ]);
  });

  it("refetches every widget when the measure changes and writes the URL", async () => {
    const user = userEvent.setup();
    const requests = trackAnalyticsRequests();

    renderDashboard();
    await screen.findByText("$812.3M");
    await waitFor(() => expect(requests).toHaveLength(3));

    await user.click(screen.getByRole("button", { name: "Base salary" }));

    expect(await screen.findByText("$666.1M")).toBeInTheDocument();
    expect(screen.getByText("$68,670")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(6));
    expect(requests.slice(3).every((url) => url.searchParams.get("measure") === "base")).toBe(true);
    expect(screen.getByTestId("location")).toHaveTextContent("measure=base");
  });

  it("applies country and department filters to every widget", async () => {
    const user = userEvent.setup();
    const requests = trackAnalyticsRequests();

    renderDashboard();
    await screen.findByText("$812.3M");
    await waitFor(() => expect(requests).toHaveLength(3));

    await user.click(screen.getByRole("combobox", { name: "Country" }));
    await user.click(await screen.findByRole("option", { name: "India" }));

    expect(await screen.findByText("$42,600 average")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(6));
    expect(requests.slice(3).every((url) => url.searchParams.get("country_code") === "IN")).toBe(
      true,
    );
    expect(screen.getByTestId("location")).toHaveTextContent("country_code=IN");

    await user.click(screen.getByRole("combobox", { name: "Department" }));
    await user.click(await screen.findByRole("option", { name: "Engineering" }));

    await waitFor(() => expect(requests).toHaveLength(9));
    expect(requests.slice(6).every((url) => url.searchParams.get("department_id") === "1")).toBe(
      true,
    );
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
    await waitFor(() => expect(requests).toHaveLength(3));
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
    );

    renderDashboard();

    expect(await screen.findByText("$0")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("No compensation data for these filters")).toBeInTheDocument();
    expect(screen.getAllByText("No data for these filters")).toHaveLength(2);
    expect(document.body).not.toHaveTextContent("NaN");
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
