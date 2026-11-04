import { request } from "./client";

export function listSalaryHistory(params) {
  return request("GET", "/salary-history", { query: params });
}
