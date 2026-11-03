import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { employeeListHandler, testEmployees } from "../test/handlers";
import { renderWithProviders } from "../test/render";
import { server } from "../test/server";
import EmployeesPage from "./EmployeesPage";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>;
}

function renderEmployees(route = "/employees") {
  return renderWithProviders(
    <>
      <LocationProbe />
      <Routes>
        <Route path="/employees" element={<EmployeesPage />} />
        <Route path="/employees/:id" element={<div>Employee detail destination</div>} />
      </Routes>
    </>,
    { route },
  );
}

function trackEmployeeRequests(total = testEmployees.length) {
  const requests = [];
  server.use(
    http.get("/api/employees", ({ request }) => {
      requests.push(new URL(request.url));
      return HttpResponse.json({
        items: testEmployees,
        total,
        page: 1,
        page_size: 25,
      });
    }),
  );
  return requests;
}

describe("EmployeesPage", () => {
  it("loads the default active page once and renders the columns and rows", async () => {
    const requests = trackEmployeeRequests();

    renderEmployees();

    expect(await screen.findByText("Asha Patel")).toBeInTheDocument();
    expect(screen.getByText("Total compensation")).toBeInTheDocument();
    await waitFor(() => expect(requests).toHaveLength(1));

    const params = requests[0].searchParams;
    expect(params.get("status")).toBe("active");
    expect(params.get("sort_by")).toBe("full_name");
    expect(params.get("sort_dir")).toBe("asc");
    expect(params.get("page")).toBe("1");
    expect(params.get("page_size")).toBe("25");
  });

  it("debounces search into one request", async () => {
    const user = userEvent.setup();
    const requests = trackEmployeeRequests();

    renderEmployees();
    await screen.findByText("Asha Patel");
    await user.type(screen.getByLabelText("Search"), "asha");

    await waitFor(() => expect(requests).toHaveLength(2), { timeout: 1500 });
    expect(requests[1].searchParams.get("q")).toBe("asha");
  });

  it("resets to page 1 when a filter changes and writes the URL", async () => {
    const user = userEvent.setup();
    const requests = trackEmployeeRequests(100);

    renderEmployees("/employees?page=3&page_size=25&status=active&sort_by=full_name&sort_dir=asc");
    await screen.findByText("Asha Patel");
    await user.click(screen.getByRole("combobox", { name: "Country" }));
    await user.click(await screen.findByRole("option", { name: "United States" }));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("country_code")).toBe("US");
    expect(requests[1].searchParams.get("page")).toBe("1");
    expect(screen.getByTestId("location")).toHaveTextContent("country_code=US");
    expect(screen.getByTestId("location")).not.toHaveTextContent("page=3");
  });

  it("sends server-side sorting and resets the page", async () => {
    const user = userEvent.setup();
    const requests = trackEmployeeRequests(100);

    renderEmployees("/employees?page=2&page_size=25&status=active&sort_by=full_name&sort_dir=asc");
    await screen.findByText("Asha Patel");
    await user.click(screen.getByText("Name"));

    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].searchParams.get("sort_by")).toBe("full_name");
    expect(requests[1].searchParams.get("sort_dir")).toBe("desc");
    expect(requests[1].searchParams.get("page")).toBe("1");
  });

  it("searches managers and applies the selected manager filter", async () => {
    const user = userEvent.setup();
    const requests = trackEmployeeRequests();

    renderEmployees();
    await screen.findByText("Asha Patel");
    await user.type(screen.getByLabelText("Manager"), "Ravi");

    await waitFor(
      () =>
        expect(
          requests.some(
            (request) =>
              request.searchParams.get("q") === "Ravi" &&
              request.searchParams.get("page_size") === "10",
          ),
        ).toBe(true),
      { timeout: 1500 },
    );

    await user.click(await screen.findByRole("option", { name: "Ravi Shah" }));

    await waitFor(() =>
      expect(requests.some((request) => request.searchParams.get("manager_id") === "2")).toBe(true),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("manager_id=2");
  });

  it("restores filters from the URL", async () => {
    const requests = trackEmployeeRequests();

    renderEmployees("/employees?q=asha&country_code=IN&status=inactive&page=2&page_size=50");

    await waitFor(() => expect(requests).toHaveLength(1));
    const params = requests[0].searchParams;
    expect(params.get("q")).toBe("asha");
    expect(params.get("country_code")).toBe("IN");
    expect(params.get("status")).toBe("inactive");
    expect(params.get("page")).toBe("2");
    expect(params.get("page_size")).toBe("50");
  });

  it("shows the empty state and clears filters", async () => {
    const user = userEvent.setup();
    server.use(employeeListHandler([], { total: 0 }));

    renderEmployees();
    expect(await screen.findByText("No employees match your filters")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);

    expect(await screen.findByText("No employees match your filters")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/employees");
    expect(screen.getByTestId("location")).not.toHaveTextContent("country_code");
  });

  it("shows an error state and retries", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get("/api/employees", () => {
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

    renderEmployees();
    expect(await screen.findByText("Could not load employees")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(calls).toBe(2));
  });

  it("opens the employee detail page when a row is clicked", async () => {
    const user = userEvent.setup();
    server.use(employeeListHandler());

    renderEmployees();
    await user.click(await screen.findByText("Asha Patel"));

    expect(await screen.findByText("Employee detail destination")).toBeInTheDocument();
  });

  it("has an add employee link", async () => {
    server.use(employeeListHandler());

    renderEmployees();

    expect(await screen.findByRole("link", { name: /add employee/i })).toHaveAttribute(
      "href",
      "/employees/new",
    );
  });
});
