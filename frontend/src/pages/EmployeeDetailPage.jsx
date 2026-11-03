import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Link as MuiLink,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink, useParams } from "react-router-dom";

import { getEmployee, getEmployeeDirectReports, getEmployeeHistory } from "../api/employees";
import { ApiError } from "../api/client";
import StatusChip from "../components/StatusChip";
import { useLookups } from "../hooks/useLookups";
import { formatDate } from "../lib/format";
import { formatLocal, formatUsd } from "../lib/money";

const HISTORY_FIELDS = [
  ["base", "base_salary_cents"],
  ["bonus", "bonus_cents"],
  ["allowances", "allowances_cents"],
];

function Field({ label, children }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.5 }}>
        {label}
      </Typography>
      <Typography component="div" sx={{ fontWeight: 600 }}>
        {children}
      </Typography>
    </Box>
  );
}

function ChangeTypeChip({ type }) {
  const styles = {
    hire: { bgcolor: "primary.light", color: "primary.main" },
    manual_edit: { bgcolor: "#EEF0F4", color: "text.secondary" },
    bulk_update: { bgcolor: "#E6F6F4", color: "secondary.main" },
  };
  const labels = {
    hire: "Hire",
    manual_edit: "Manual edit",
    bulk_update: "Bulk update",
  };

  return <Chip size="small" label={labels[type] ?? type} sx={styles[type]} />;
}

function percentChange(current, previous) {
  if (!previous) {
    return null;
  }
  const percent = ((current - previous) / previous) * 100;
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(1)}%`;
}

function HistoryEntry({ row }) {
  const changedFields = HISTORY_FIELDS.filter(
    ([, key]) => row.previous === null || row.new[key] !== row.previous[key],
  );

  return (
    <Box
      sx={{
        position: "relative",
        "&:before": {
          content: '""',
          position: "absolute",
          left: -17,
          top: 6,
          width: 10,
          height: 10,
          borderRadius: "50%",
          bgcolor: "background.paper",
          border: "2px solid",
          borderColor: row.change_type === "manual_edit" ? "text.secondary" : "primary.main",
        },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1 }}>
        <Typography sx={{ fontWeight: 600 }}>{formatDate(row.effective_date)}</Typography>
        <ChangeTypeChip type={row.change_type} />
        {row.reason ? <Typography color="text.secondary">{row.reason}</Typography> : null}
        {row.batch_id ? (
          <Typography variant="caption" color="text.secondary">
            Batch {row.batch_id.slice(0, 8)}
          </Typography>
        ) : null}
      </Box>
      <Box sx={{ mt: 0.5 }}>
        {changedFields.map(([label, key]) => {
          const previous = row.previous?.[key];
          const percent =
            key === "base_salary_cents" ? percentChange(row.new[key], previous) : null;
          return (
            <Typography key={key} variant="body1" sx={{ fontFamily: "monospace" }}>
              {`${label} ${formatUsd(row.new[key])}`}
              {previous != null ? ` from ${formatUsd(previous)}` : ""}
              {percent ? ` (${percent})` : ""}
            </Typography>
          );
        })}
      </Box>
    </Box>
  );
}

function NotFoundState() {
  return (
    <Card>
      <CardContent sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h1" component="h1">
          Employee not found
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
          This employee does not exist or is no longer available.
        </Typography>
        <Button component={RouterLink} to="/employees" variant="contained">
          Back to employees
        </Button>
      </CardContent>
    </Card>
  );
}

export default function EmployeeDetailPage() {
  const { id } = useParams();
  const [reportsPage, setReportsPage] = useState(1);
  const lookups = useLookups();
  const employeeQuery = useQuery({
    queryKey: ["employee", id],
    queryFn: () => getEmployee(id),
    retry: false,
    enabled: Boolean(id),
  });
  const historyQuery = useQuery({
    queryKey: ["employee", id, "history"],
    queryFn: () => getEmployeeHistory(id),
    retry: false,
    enabled: Boolean(id) && employeeQuery.isSuccess,
  });
  const reportsQuery = useQuery({
    queryKey: ["employee", id, "reports", reportsPage],
    queryFn: () => getEmployeeDirectReports(id, { page: reportsPage, page_size: 25 }),
    retry: false,
    enabled: Boolean(id) && employeeQuery.isSuccess,
  });

  if (employeeQuery.isLoading) {
    return (
      <Box sx={{ minHeight: 320, display: "grid", placeItems: "center" }}>
        <CircularProgress aria-label="Loading employee" />
      </Box>
    );
  }

  if (employeeQuery.isError) {
    if (employeeQuery.error instanceof ApiError && employeeQuery.error.status === 404) {
      return <NotFoundState />;
    }
    return (
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={() => employeeQuery.refetch()}>
            Retry
          </Button>
        }
      >
        Could not load employee
      </Alert>
    );
  }

  const employee = employeeQuery.data;
  const local = employee.local;
  const rate = lookups.data?.currency_rates.find(
    (currencyRate) => currencyRate.currency_code === local.currency_code,
  );
  const updatedOn = rate ? `, updated ${formatDate(rate.updated_at.slice(0, 10))}` : "";
  const reports = reportsQuery.data?.items ?? [];
  const reportsTotal = reportsQuery.data?.total ?? 0;
  const history = historyQuery.data ?? [];

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <MuiLink component={RouterLink} to="/employees">
          Employees
        </MuiLink>
        <Typography color="text.disabled">/</Typography>
        <Typography sx={{ fontWeight: 600 }}>{employee.full_name}</Typography>
      </Box>

      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          alignItems: { sm: "center" },
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 1.5 }}>
          <Typography variant="h1" component="h1">
            {employee.full_name}
          </Typography>
          <Typography variant="h3" color="text.secondary">
            {employee.job_title.name}
          </Typography>
          <StatusChip status={employee.status} />
        </Box>
        <Button component={RouterLink} to={`/employees/${employee.id}/edit`} variant="outlined">
          Edit
        </Button>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h2" sx={{ pb: 2, borderBottom: 1, borderColor: "divider" }}>
              Profile
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                gap: 2,
                pt: 2,
              }}
            >
              <Field label="Email">{employee.email}</Field>
              <Field label="Department">{employee.department.name}</Field>
              <Field label="Country">{employee.country.name}</Field>
              <Field label="Hire date">{formatDate(employee.hire_date)}</Field>
              <Field label="Manager">
                {employee.manager ? (
                  <MuiLink component={RouterLink} to={`/employees/${employee.manager.id}`}>
                    {employee.manager.full_name}
                  </MuiLink>
                ) : (
                  "—"
                )}
              </Field>
              <Field label="Direct reports count">{employee.direct_reports_count}</Field>
            </Box>
          </CardContent>
        </Card>

        <Card>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h2" sx={{ pb: 2, borderBottom: 1, borderColor: "divider" }}>
              Compensation (USD)
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1, pt: 2 }}>
              {[
                ["Base", employee.base_salary_cents],
                ["Bonus", employee.bonus_cents],
                ["Allowances", employee.allowances_cents],
              ].map(([label, value]) => (
                <Box key={label} sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography color="text.secondary">{label}</Typography>
                  <Typography sx={{ fontFamily: "monospace" }}>{formatUsd(value)}</Typography>
                </Box>
              ))}
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  borderTop: 1,
                  borderColor: "divider",
                  pt: 1.5,
                  mt: 0.5,
                }}
              >
                <Typography sx={{ fontWeight: 600 }}>Total</Typography>
                <Typography variant="h2" sx={{ fontFamily: "monospace" }}>
                  {formatUsd(employee.total_comp_cents)}
                </Typography>
              </Box>
            </Box>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 2, pt: 2, borderTop: 1, borderColor: "divider" }}
            >
              {`Approximate: ${formatLocal(local.total_comp_cents, local.currency_code)} ${local.currency_code} (static rate${updatedOn})`}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h2" sx={{ pb: 2, borderBottom: 1, borderColor: "divider" }}>
            Reporting
          </Typography>
          <Box sx={{ display: "flex", gap: 1, pt: 2 }}>
            <Typography color="text.secondary">Manager:</Typography>
            {employee.manager ? (
              <MuiLink component={RouterLink} to={`/employees/${employee.manager.id}`}>
                {employee.manager.full_name}
              </MuiLink>
            ) : (
              <Typography>—</Typography>
            )}
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h2" sx={{ pb: 2, borderBottom: 1, borderColor: "divider" }}>
            Direct reports
          </Typography>

          {reportsQuery.isLoading ? (
            <Box sx={{ py: 3, display: "grid", placeItems: "center" }}>
              <CircularProgress size={24} aria-label="Loading direct reports" />
            </Box>
          ) : reports.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 2, fontStyle: "italic" }}>
              No direct reports
            </Typography>
          ) : (
            <>
              <Table size="small" sx={{ mt: 2 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Job title</TableCell>
                    <TableCell align="right">Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow key={report.id} hover>
                      <TableCell>
                        <MuiLink component={RouterLink} to={`/employees/${report.id}`}>
                          {report.full_name}
                        </MuiLink>
                      </TableCell>
                      <TableCell>{report.job_title.name}</TableCell>
                      <TableCell align="right">
                        <StatusChip status={report.status} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={reportsTotal}
                page={reportsPage - 1}
                onPageChange={(_, nextPage) => setReportsPage(nextPage + 1)}
                rowsPerPage={25}
                rowsPerPageOptions={[]}
              />
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h2" sx={{ pb: 2, borderBottom: 1, borderColor: "divider" }}>
            Salary history
          </Typography>
          {history.length === 0 ? (
            <Typography color="text.secondary" sx={{ py: 2, fontStyle: "italic" }}>
              No salary history
            </Typography>
          ) : (
            <Box
              sx={{
                position: "relative",
                pl: 3,
                mt: 3,
                display: "flex",
                flexDirection: "column",
                gap: 3,
                "&:before": {
                  content: '""',
                  position: "absolute",
                  left: 4,
                  top: 6,
                  bottom: 6,
                  width: 2,
                  bgcolor: "divider",
                },
              }}
            >
              {history.map((row) => (
                <HistoryEntry key={row.id} row={row} />
              ))}
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
