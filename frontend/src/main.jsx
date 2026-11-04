import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "./auth/AuthProvider";
import ErrorBoundary from "./components/ErrorBoundary";
import { installGlobalErrorLogging } from "./lib/logger";
import AppRoutes from "./router";
import theme from "./theme";

const queryClient = new QueryClient();

installGlobalErrorLogging();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <ErrorBoundary>
            <AuthProvider>
              <AppRoutes />
            </AuthProvider>
          </ErrorBoundary>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
