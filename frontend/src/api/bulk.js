import { request } from "./client";

export function previewBulkUpdate(body) {
  return request("POST", "/bulk-updates/preview", { body });
}

export function applyBulkUpdate(body) {
  return request("POST", "/bulk-updates/apply", { body });
}
