import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { getMe, login as loginRequest, logout as logoutRequest } from "../api/auth";
import { setCsrfToken, setUnauthorizedHandler } from "../api/client";
import { AuthContext } from "./useAuth";

const ANONYMOUS = { user: null, csrfToken: null, status: "anonymous" };

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState({ user: null, csrfToken: null, status: "loading" });
  const bootstrapping = useRef(true);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    let active = true;
    bootstrapping.current = true;

    getMe()
      .then((response) => {
        if (!active) {
          return;
        }
        setCsrfToken(response.csrf_token);
        setAuth({
          user: response.user,
          csrfToken: response.csrf_token,
          status: "authenticated",
        });
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setCsrfToken(null);
        setAuth(ANONYMOUS);
      })
      .finally(() => {
        if (active) {
          bootstrapping.current = false;
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      if (bootstrapping.current) {
        return;
      }

      setCsrfToken(null);
      setAuth(ANONYMOUS);
      queryClient.clear();

      if (location.pathname !== "/login") {
        navigate("/login", {
          replace: true,
          state: { from: `${location.pathname}${location.search}${location.hash}` },
        });
      }
    };

    setUnauthorizedHandler(handleUnauthorized);
    return () => setUnauthorizedHandler(null);
  }, [location.hash, location.pathname, location.search, navigate, queryClient]);

  const login = useCallback(async (credentials) => {
    const response = await loginRequest(credentials);
    setCsrfToken(response.csrf_token);
    setAuth({
      user: response.user,
      csrfToken: response.csrf_token,
      status: "authenticated",
    });
    return response;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // The local session is cleared even if the server cannot be reached.
    } finally {
      setCsrfToken(null);
      setAuth(ANONYMOUS);
      queryClient.clear();
      navigate("/login", { replace: true });
    }
  }, [navigate, queryClient]);

  const value = useMemo(() => ({ ...auth, login, logout }), [auth, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
