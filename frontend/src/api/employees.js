import { request } from "./client";

export function listEmployees(params) {
  return request("GET", "/employees", { query: params });
}

export function createEmployee(body) {
  return request("POST", "/employees", { body });
}

export function getEmployee(id) {
  return request("GET", `/employees/${id}`);
}

export function getEmployeeHistory(id) {
  return request("GET", `/employees/${id}/history`);
}

export function getEmployeeDirectReports(id, params) {
  return request("GET", `/employees/${id}/direct-reports`, { query: params });
}
