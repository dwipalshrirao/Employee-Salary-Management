const API_BASE = "/api";
const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

let csrfToken = null;
let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function setCsrfToken(token) {
  csrfToken = token;
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

export async function request(method, path, { query, body } = {}) {
  const normalizedMethod = method.toUpperCase();
  const headers = { Accept: "application/json" };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (WRITE_METHODS.has(normalizedMethod) && csrfToken) {
    headers["X-CSRF-Token"] = csrfToken;
  }

  const response = await fetch(buildUrl(path, query), {
    method: normalizedMethod,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await parseResponse(response);

  if (!response.ok) {
    if (response.status === 401 && !isLoginPath(path)) {
      unauthorizedHandler?.();
    }
    throw toApiError(response, payload);
  }

  return payload;
}

function buildUrl(path, query) {
  const normalizedPath = path.startsWith("/api")
    ? path
    : `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  if (!query) {
    return normalizedPath;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    params.append(key, String(value));
  }

  const queryString = params.toString();
  return queryString ? `${normalizedPath}?${queryString}` : normalizedPath;
}

async function parseResponse(response) {
  if (response.status === 204) {
    return undefined;
  }

  const text = await response.text();
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function toApiError(response, payload) {
  const error = payload?.error;

  return new ApiError(
    response.status,
    error?.code ?? "request_failed",
    error?.message ?? `Request failed with status ${response.status}`,
    error?.details ?? {},
  );
}

function isLoginPath(path) {
  return path === "/auth/login" || path === "/api/auth/login";
}
