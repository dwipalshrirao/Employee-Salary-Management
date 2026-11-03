import { request } from "./client";

export function getLookups() {
  return request("GET", "/lookups");
}
