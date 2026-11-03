import { Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import PlaceholderPage from "./pages/PlaceholderPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PlaceholderPage title="Login" />} />
      <Route element={<AppShell />}>
        <Route index element={<PlaceholderPage title="Dashboard" />} />
        <Route path="employees" element={<PlaceholderPage title="Employees" />} />
        <Route path="employees/new" element={<PlaceholderPage title="Add employee" />} />
        <Route path="employees/:id" element={<PlaceholderPage title="Employee detail" />} />
        <Route path="employees/:id/edit" element={<PlaceholderPage title="Edit employee" />} />
        <Route path="history" element={<PlaceholderPage title="Salary history" />} />
        <Route path="bulk-update" element={<PlaceholderPage title="Bulk update" />} />
        <Route path="*" element={<PlaceholderPage title="Not found" />} />
      </Route>
    </Routes>
  );
}
