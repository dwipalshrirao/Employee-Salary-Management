import { request } from "./client";

export function listEmployees(params) {
  return request("GET", "/employees", { query: params });
}
