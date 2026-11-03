import { request } from "./client";

/**
 * @typedef {Object} AuthUser
 * @property {number} id
 * @property {string} email
 * @property {string} full_name
 *
 * @typedef {Object} AuthResponse
 * @property {AuthUser} user
 * @property {string} csrf_token
 */

export function login(credentials) {
  return request("POST", "/auth/login", { body: credentials });
}

export function getMe() {
  return request("GET", "/auth/me");
}

export function logout() {
  return request("POST", "/auth/logout");
}
