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

const analyticsCountryRows = [
  {
    key: "US",
    name: "United States",
    headcount: 2700,
    total_cents: 31_914_000_000,
    avg_cents: 11_820_000,
    min_cents: 4_500_000,
    max_cents: 35_000_000,
  },
  {
    key: "SG",
    name: "Singapore",
    headcount: 1200,
    total_cents: 12_288_000_000,
    avg_cents: 10_240_000,
    min_cents: 4_200_000,
    max_cents: 28_000_000,
  },
  {
    key: "CA",
    name: "Canada",
    headcount: 900,
    total_cents: 8_262_000_000,
    avg_cents: 9_180_000,
    min_cents: 4_000_000,
    max_cents: 24_000_000,
  },
  {
    key: "DE",
    name: "Germany",
    headcount: 1200,
    total_cents: 10_500_000_000,
    avg_cents: 8_750_000,
    min_cents: 3_800_000,
    max_cents: 25_000_000,
  },
  {
    key: "GB",
    name: "United Kingdom",
    headcount: 1200,
    total_cents: 10_092_000_000,
    avg_cents: 8_410_000,
    min_cents: 3_600_000,
    max_cents: 23_000_000,
  },
  {
    key: "IN",
    name: "India",
    headcount: 2500,
    total_cents: 10_650_000_000,
    avg_cents: 4_260_000,
    min_cents: 1_500_000,
    max_cents: 18_000_000,
  },
];

const analyticsDepartmentRows = [
  {
    key: "1",
    name: "Engineering",
    headcount: 3000,
    total_cents: 33_600_000_000,
    avg_cents: 11_200_000,
    min_cents: 4_500_000,
    max_cents: 35_000_000,
  },
  {
    key: "2",
    name: "Product",
    headcount: 800,
    total_cents: 8_680_000_000,
    avg_cents: 10_850_000,
    min_cents: 4_200_000,
    max_cents: 30_000_000,
  },
  {
    key: "3",
    name: "Sales",
    headcount: 1800,
    total_cents: 16_956_000_000,
    avg_cents: 9_420_000,
    min_cents: 3_800_000,
    max_cents: 28_000_000,
  },
  {
    key: "4",
    name: "Finance",
    headcount: 700,
    total_cents: 6_237_000_000,
    avg_cents: 8_910_000,
    min_cents: 3_600_000,
    max_cents: 24_000_000,
  },
  {
    key: "5",
    name: "Marketing",
    headcount: 800,
    total_cents: 6_272_000_000,
    avg_cents: 7_840_000,
    min_cents: 3_400_000,
    max_cents: 22_000_000,
  },
  {
    key: "6",
    name: "Human Resources",
    headcount: 500,
    total_cents: 3_630_000_000,
    avg_cents: 7_260_000,
    min_cents: 3_200_000,
    max_cents: 20_000_000,
  },
  {
    key: "7",
    name: "Operations",
    headcount: 1000,
    total_cents: 6_430_000_000,
    avg_cents: 6_430_000,
    min_cents: 3_000_000,
    max_cents: 18_000_000,
  },
  {
    key: "8",
    name: "Customer Support",
    headcount: 1100,
    total_cents: 5_632_000_000,
    avg_cents: 5_120_000,
    min_cents: 2_800_000,
    max_cents: 16_000_000,
  },
];

export const testAnalyticsSummary = {
  headcount: 9700,
  total_cents: 81_230_000_000,
  avg_cents: 8_374_000,
  min_cents: 3_000_000,
  max_cents: 35_000_000,
  components: {
    base_cents: 66_610_000_000,
    bonus_cents: 8_904_000_000,
    allowances_cents: 5_716_000_000,
  },
  country_count: 6,
  department_count: 9,
};

export const testAnalyticsBaseSummary = {
  ...testAnalyticsSummary,
  total_cents: 66_610_000_000,
  avg_cents: 6_867_000,
};

export const testAnalyticsCountryBreakdown = {
  group_by: "country",
  measure: "total",
  rows: analyticsCountryRows,
};

export const testAnalyticsDepartmentBreakdown = {
  group_by: "department",
  measure: "total",
  rows: analyticsDepartmentRows,
};

export const analyticsHandlers = [
  http.get("/api/analytics/summary", ({ request }) => {
    const measure = new URL(request.url).searchParams.get("measure");
    return HttpResponse.json(measure === "base" ? testAnalyticsBaseSummary : testAnalyticsSummary);
  }),
  http.get("/api/analytics/breakdown", ({ request }) => {
    const url = new URL(request.url);
    const groupBy = url.searchParams.get("group_by");
    const measure = url.searchParams.get("measure") ?? "total";
    const countryCode = url.searchParams.get("country_code");
    const departmentId = url.searchParams.get("department_id");
    if (groupBy === "department") {
      const rows = departmentId
        ? analyticsDepartmentRows.filter((row) => row.key === departmentId)
        : analyticsDepartmentRows;
      return HttpResponse.json({
        ...testAnalyticsDepartmentBreakdown,
        measure,
        rows,
      });
    }
    const rows = countryCode
      ? analyticsCountryRows.filter((row) => row.key === countryCode)
      : analyticsCountryRows;
    return HttpResponse.json({
      ...testAnalyticsCountryBreakdown,
      measure,
      rows,
    });
  }),
];

export const testSalaryHistoryPage = {
  items: [
    {
      id: 31,
      employee: {
        id: 1,
        full_name: "Asha Patel",
        email: "asha.patel@acme.example",
      },
      effective_date: "2026-10-31",
      change_type: "bulk_update",
      reason: "FY27 raise",
      batch_id: "6f1c8a00-0000-0000-0000-000000000000",
      created_at: "2026-10-31T12:00:00Z",
      new: {
        base_salary_cents: 4_500_000,
        bonus_cents: 450_000,
        allowances_cents: 180_000,
        total_comp_cents: 5_130_000,
      },
      previous: {
        base_salary_cents: 4_285_700,
        bonus_cents: 450_000,
        allowances_cents: 180_000,
        total_comp_cents: 4_915_700,
      },
    },
    {
      id: 30,
      employee: {
        id: 4,
        full_name: "Priya Nair",
        email: "priya.nair@acme.example",
      },
      effective_date: "2026-10-15",
      change_type: "manual_edit",
      reason: "Promotion",
      batch_id: null,
      created_at: "2026-10-15T12:00:00Z",
      new: {
        base_salary_cents: 7_200_000,
        bonus_cents: 800_000,
        allowances_cents: 0,
        total_comp_cents: 8_000_000,
      },
      previous: {
        base_salary_cents: 6_500_000,
        bonus_cents: 650_000,
        allowances_cents: 0,
        total_comp_cents: 7_150_000,
      },
    },
    {
      id: 1,
      employee: {
        id: 5,
        full_name: "Sophie Turner",
        email: "sophie.turner@acme.example",
      },
      effective_date: "2021-04-12",
      change_type: "hire",
      reason: "New hire",
      batch_id: null,
      created_at: "2021-04-12T12:00:00Z",
      new: {
        base_salary_cents: 11_500_000,
        bonus_cents: 1_200_000,
        allowances_cents: 500_000,
        total_comp_cents: 13_200_000,
      },
      previous: null,
    },
  ],
  total: 3,
  page: 1,
  page_size: 25,
};

export function salaryHistoryHandler(items = testSalaryHistoryPage.items, overrides = {}) {
  return http.get("/api/salary-history", () =>
    HttpResponse.json({
      ...testSalaryHistoryPage,
      items,
      total: items.length,
      ...overrides,
    }),
  );
}

export const testBulkPreview = {
  component: "base",
  mode: "percent",
  affected_count: 2,
  sum_before_cents: 8_500_000,
  sum_after_cents: 8_925_000,
  sum_delta_cents: 425_000,
  sample: [
    { id: 1, full_name: "Asha Patel", before_cents: 4_500_000, after_cents: 4_725_000 },
    { id: 2, full_name: "Ravi Shah", before_cents: 4_000_000, after_cents: 4_200_000 },
  ],
};

export const testBulkApply = {
  batch_id: "6f1c8a00-0000-0000-0000-000000000000",
  component: "base",
  affected_count: 2,
  sum_delta_cents: 425_000,
};

export const bulkHandlers = [
  http.post("/api/bulk-updates/preview", () => HttpResponse.json(testBulkPreview)),
  http.post("/api/bulk-updates/apply", () => HttpResponse.json(testBulkApply)),
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

export const handlers = [
  ...authHandlers,
  ...dataHandlers,
  ...detailHandlers,
  ...bulkHandlers,
  salaryHistoryHandler(),
  ...analyticsHandlers,
];
