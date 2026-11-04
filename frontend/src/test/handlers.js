import { http, HttpResponse } from "msw";

export const testUser = {
  id: 1,
  email: "hr@acme.example",
  full_name: "HR Manager",
};

export const authResponse = {
  user: testUser,
  csrf_token: "test-csrf-token",
};

export function unauthorizedResponse() {
  return HttpResponse.json(
    {
      error: {
        code: "unauthorized",
        message: "Authentication required.",
        details: {},
      },
    },
    { status: 401 },
  );
}

export function signedInMeHandler() {
  return http.get("/api/auth/me", () => HttpResponse.json(authResponse));
}

export const authHandlers = [
  http.get("/api/auth/me", () => unauthorizedResponse()),
  http.post("/api/auth/login", async ({ request }) => {
    const body = await request.json();
    if (body.email === testUser.email && body.password === "correct-password") {
      return HttpResponse.json(authResponse);
    }
    return HttpResponse.json(
      {
        error: {
          code: "unauthorized",
          message: "Invalid email or password",
          details: {},
        },
      },
      { status: 401 },
    );
  }),
  http.post("/api/auth/logout", () => new HttpResponse(null, { status: 204 })),
];

export const testLookups = {
  countries: [
    { code: "IN", name: "India", currency_code: "INR" },
    { code: "US", name: "United States", currency_code: "USD" },
  ],
  departments: [
    { id: 1, name: "Engineering" },
    { id: 2, name: "Sales" },
  ],
  job_titles: [
    { id: 1, name: "Software Engineer", level: 2 },
    { id: 2, name: "Account Executive", level: 2 },
  ],
  currency_rates: [
    { currency_code: "USD", rate_per_usd: 1.0, updated_at: "2026-01-01T00:00:00Z" },
    { currency_code: "INR", rate_per_usd: 83.0, updated_at: "2026-01-01T00:00:00Z" },
  ],
};

export const testEmployees = [
  {
    id: 1,
    full_name: "Asha Patel",
    email: "asha.patel@acme.example",
    department: { id: 1, name: "Engineering" },
    job_title: { id: 1, name: "Software Engineer" },
    country: { code: "IN", name: "India" },
    manager: { id: 2, full_name: "Ravi Shah" },
    hire_date: "2021-04-12",
    status: "active",
    base_salary_cents: 4_500_000,
    bonus_cents: 450_000,
    allowances_cents: 180_000,
    total_comp_cents: 5_130_000,
  },
  {
    id: 2,
    full_name: "Ravi Shah",
    email: "ravi.shah@acme.example",
    department: { id: 1, name: "Engineering" },
    job_title: { id: 1, name: "Software Engineer" },
    country: { code: "US", name: "United States" },
    manager: null,
    hire_date: "2019-02-01",
    status: "active",
    base_salary_cents: 6_500_000,
    bonus_cents: 650_000,
    allowances_cents: 260_000,
    total_comp_cents: 7_410_000,
  },
];

export const testEmployeeDetail = {
  ...testEmployees[0],
  direct_reports_count: 1,
  local: {
    currency_code: "INR",
    rate_per_usd: 83.0,
    base_salary_cents: 373_500_000,
    bonus_cents: 37_350_000,
    allowances_cents: 14_940_000,
    total_comp_cents: 425_790_000,
  },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};

export const testDirectReports = {
  items: [
    {
      id: 3,
      full_name: "John Smith",
      email: "john.smith@acme.example",
      department: { id: 2, name: "Sales" },
      job_title: { id: 2, name: "Account Executive" },
      country: { code: "US", name: "United States" },
      manager: { id: 1, full_name: "Asha Patel" },
      hire_date: "2023-03-06",
      status: "active",
      base_salary_cents: 3_200_000,
      bonus_cents: 320_000,
      allowances_cents: 128_000,
      total_comp_cents: 3_648_000,
    },
  ],
  total: 1,
  page: 1,
  page_size: 25,
};

export const testHistory = [
  {
    id: 12,
    effective_date: "2025-03-01",
    change_type: "manual_edit",
    reason: "Annual review",
    batch_id: null,
    created_at: "2025-03-01T12:00:00Z",
    new: {
      base_salary_cents: 4_500_000,
      bonus_cents: 450_000,
      allowances_cents: 180_000,
      total_comp_cents: 5_130_000,
    },
    previous: {
      base_salary_cents: 4_000_000,
      bonus_cents: 400_000,
      allowances_cents: 100_000,
      total_comp_cents: 4_500_000,
    },
  },
  {
    id: 11,
    effective_date: "2021-04-12",
    change_type: "hire",
    reason: "New hire",
    batch_id: null,
    created_at: "2021-04-12T12:00:00Z",
    new: {
      base_salary_cents: 4_000_000,
      bonus_cents: 400_000,
      allowances_cents: 100_000,
      total_comp_cents: 4_500_000,
    },
    previous: null,
  },
];

export function notFoundResponse() {
  return HttpResponse.json(
    {
      error: {
        code: "not_found",
        message: "Not found.",
        details: {},
      },
    },
    { status: 404 },
  );
}

export const detailHandlers = [
  http.get("/api/employees/:id", ({ params }) =>
    params.id === "1" ? HttpResponse.json(testEmployeeDetail) : notFoundResponse(),
  ),
  http.get("/api/employees/:id/direct-reports", ({ params }) =>
    params.id === "1" ? HttpResponse.json(testDirectReports) : notFoundResponse(),
  ),
  http.get("/api/employees/:id/history", ({ params }) =>
    params.id === "1" ? HttpResponse.json(testHistory) : notFoundResponse(),
  ),
  http.patch("/api/employees/:id", async ({ request, params }) => {
    if (params.id !== "1") {
      return notFoundResponse();
    }
    const body = await request.json();
    return HttpResponse.json({ ...testEmployeeDetail, ...body });
  }),
  http.post("/api/employees/:id/deactivate", ({ params }) =>
    params.id === "1"
      ? HttpResponse.json({ ...testEmployeeDetail, status: "inactive" })
      : notFoundResponse(),
  ),
  http.post("/api/employees/:id/reactivate", ({ params }) =>
    params.id === "1"
      ? HttpResponse.json({ ...testEmployeeDetail, status: "active" })
      : notFoundResponse(),
  ),
];

export function employeeListHandler(items = testEmployees, overrides = {}) {
  return http.get("/api/employees", () =>
    HttpResponse.json({
      items,
      total: items.length,
      page: 1,
      page_size: 25,
      ...overrides,
    }),
  );
}

export const dataHandlers = [
  http.get("/api/lookups", () => HttpResponse.json(testLookups)),
  employeeListHandler(),
  http.post("/api/employees", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      {
        ...testEmployeeDetail,
        id: 99,
        full_name: body.full_name,
        email: body.email,
      },
      { status: 201 },
    );
  }),
];

export const handlers = [...authHandlers, ...dataHandlers, ...detailHandlers];
