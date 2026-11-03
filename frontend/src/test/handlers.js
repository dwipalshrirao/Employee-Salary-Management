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
];

export const handlers = [...authHandlers, ...dataHandlers];
