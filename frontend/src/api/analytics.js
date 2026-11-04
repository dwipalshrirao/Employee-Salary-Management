import { request } from "./client";

export function getAnalyticsSummary(params) {
  return request("GET", "/analytics/summary", { query: params });
}

export function getAnalyticsBreakdown(params) {
  return request("GET", "/analytics/breakdown", { query: params });
}

export function getAnalyticsDistribution(params) {
  return request("GET", "/analytics/distribution", { query: params });
}

export function getAnalyticsOutliers(params) {
  return request("GET", "/analytics/outliers", { query: params });
}

export function getAnalyticsTeam(managerId) {
  return request("GET", `/analytics/team/${managerId}`);
}
