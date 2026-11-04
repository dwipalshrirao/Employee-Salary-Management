import { request } from "./client";

export function getAnalyticsSummary(params) {
  return request("GET", "/analytics/summary", { query: params });
}

export function getAnalyticsBreakdown(params) {
  return request("GET", "/analytics/breakdown", { query: params });
}
