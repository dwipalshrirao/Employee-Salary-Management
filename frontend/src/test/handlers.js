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

export const handlers = [...authHandlers];
