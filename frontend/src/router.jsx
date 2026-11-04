import { lazy, Suspense } from "react";
import { Box, CircularProgress } from "@mui/material";
import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import AppShell from "./components/AppShell";
import BulkUpdatePage from "./pages/BulkUpdatePage";
import EmployeeDetailPage from "./pages/EmployeeDetailPage";
import EmployeeFormPage from "./pages/EmployeeFormPage";
import EmployeesPage from "./pages/EmployeesPage";
import HistoryPage from "./pages/HistoryPage";
import LoginPage from "./pages/LoginPage";
import PlaceholderPage from "./pages/PlaceholderPage";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));

function DashboardRoute() {
  return (
    <Suspense
      fallback={
        <Box sx={{ minHeight: 320, display: "grid", placeItems: "center" }}>
          <CircularProgress aria-label="Loading dashboard" />
        </Box>
      }
    >
      <DashboardPage />
    </Suspense>
  );
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardRoute />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="employees/new" element={<EmployeeFormPage />} />
          <Route path="employees/:id" element={<EmployeeDetailPage />} />
          <Route path="employees/:id/edit" element={<EmployeeFormPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="bulk-update" element={<BulkUpdatePage />} />
        </Route>
      </Route>
      <Route path="*" element={<PlaceholderPage title="Not found" />} />
    </Routes>
  );
}
