import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, Chip, MenuItem, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { listSalaryHistory } from "../api/history";
import { useDebounce } from "../hooks/useDebounce";
import { useUrlState } from "../hooks/useUrlState";
import { formatDate } from "../lib/format";
import { formatUsd } from "../lib/money";

const DEFAULT_STATE = {
  employee: "",
  reason: "",
  change_type: "",
  date_from: "",
  date_to: "",
  batch_id: "",
  sort_by: "effective_date",
  sort_dir: "desc",
  page: "1",
  page_size: "25",
};

const SORTABLE_FIELDS = new Set(["effective_date", "employee", "change_type"]);
const SALARY_COLUMNS = [
  { field: "base_salary", headerName: "Base salary", key: "base_salary_cents" },
  { field: "bonus", headerName: "Bonus", key: "bonus_cents" },
  { field: "allowances", headerName: "Allowances", key: "allowances_cents" },
];

const CHANGE_TYPE_LABELS = {
  hire: "Hire",
  manual_edit: "Manual edit",
  bulk_update: "Bulk update",
};

const CHANGE_TYPE_STYLES = {
  hire: { bgcolor: "primary.light", color: "primary.main" },
  manual_edit: { bgcolor: "#EEF0F4", color: "text.secondary" },
  bulk_update: { bgcolor: "#E6F6F4", color: "secondary.main" },
};

function numberParam(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function historyQuery(values) {
  const query = {
    sort_by: SORTABLE_FIELDS.has(values.sort_by) ? values.sort_by : DEFAULT_STATE.sort_by,
    sort_dir: values.sort_dir === "asc" ? "asc" : "desc",
    page: numberParam(values.page, 1),
    page_size: numberParam(values.page_size, 25),
  };
  for (const key of ["employee", "reason", "change_type", "date_from", "date_to", "batch_id"]) {
    if (values[key]) {
      query[key] = values[key];
    }
  }
  return query;
}

function percentChange(current, previous) {
  if (previous == null || previous === 0 || current == null) {
    return null;
  }
  const change = ((current - previous) / previous) * 100;
  return `${change >= 0 ? "+" : ""}${change.toFixed(1)}%`;
}

function ChangeTypeChip({ type }) {
  return (
    <Chip size="small" label={CHANGE_TYPE_LABELS[type] ?? type} sx={CHANGE_TYPE_STYLES[type]} />
  );
}

function SalaryCell({ row, fieldKey }) {
  const current = row.new[fieldKey];
  const previous = row.previous?.[fieldKey] ?? null;

  if (row.change_type === "hire") {
    return <Typography sx={{ fontSize: 14 }}>{formatUsd(current)}</Typography>;
  }

  if (previous === null || previous === current) {
    return <Typography color="text.secondary">—</Typography>;
  }

  const percent = percentChange(current, previous);
  return (
    <Box>
      <Typography sx={{ fontSize: 14 }}>{`${formatUsd(previous)} → ${formatUsd(
        current,
      )}`}</Typography>
      {percent ? (
        <Typography variant="caption" color="text.secondary">
          {percent}
        </Typography>
      ) : null}
    </Box>
  );
}

const columns = [
  {
    field: "effective_date",
    headerName: "Date",
    minWidth: 120,
    flex: 0.8,
    renderCell: (params) => formatDate(params.value),
  },
  {
    field: "employee",
    headerName: "Employee",
    minWidth: 170,
    flex: 1.1,
    valueGetter: (value) => value?.full_name,
    renderCell: (params) => (
      <Typography
        component={RouterLink}
        to={`/employees/${params.row.employee.id}`}
        color="primary"
        onClick={(event) => event.stopPropagation()}
        sx={{ fontWeight: 500, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
      >
        {params.row.employee.full_name}
      </Typography>
    ),
  },
  {
    field: "change_type",
    headerName: "Type",
    minWidth: 130,
    flex: 0.8,
    renderCell: (params) => <ChangeTypeChip type={params.value} />,
  },
  {
    field: "reason",
    headerName: "Reason",
    minWidth: 180,
    flex: 1.3,
    valueGetter: (value) => value || "—",
  },
  ...SALARY_COLUMNS.map((column) => ({
    field: column.field,
    headerName: column.headerName,
    minWidth: 170,
    flex: 1.3,
    sortable: false,
    renderCell: (params) => <SalaryCell row={params.row} fieldKey={column.key} />,
  })),
];

export default function HistoryPage() {
  const navigate = useNavigate();
  const { values, update, reset } = useUrlState(DEFAULT_STATE);
  const [employeeInput, setEmployeeInput] = useState(values.employee);
  const [reasonInput, setReasonInput] = useState(values.reason);
  const debouncedEmployee = useDebounce(employeeInput, 300);
  const debouncedReason = useDebounce(reasonInput, 300);
  const query = historyQuery(values);
  const historyQueryResult = useQuery({
    queryKey: ["history", query],
    queryFn: () => listSalaryHistory(query),
    placeholderData: keepPreviousData,
  });

  useEffect(() => {
    setEmployeeInput(values.employee);
  }, [values.employee]);

  useEffect(() => {
    setReasonInput(values.reason);
  }, [values.reason]);

  useEffect(() => {
    if (debouncedEmployee === employeeInput && debouncedEmployee !== values.employee) {
      update({ employee: debouncedEmployee, page: "1" });
    }
  }, [debouncedEmployee, employeeInput, update, values.employee]);

  useEffect(() => {
    if (debouncedReason === reasonInput && debouncedReason !== values.reason) {
      update({ reason: debouncedReason, page: "1" });
    }
  }, [debouncedReason, reasonInput, update, values.reason]);

  const pageSize = numberParam(values.page_size, 25);
  const page = numberParam(values.page, 1);
  const sortBy = SORTABLE_FIELDS.has(values.sort_by) ? values.sort_by : DEFAULT_STATE.sort_by;
  const sortDir = values.sort_dir === "asc" ? "asc" : "desc";

  const applyFilter = (key, value) => update({ [key]: value, page: "1" });
  const clearFilters = () => {
    setEmployeeInput("");
    setReasonInput("");
    reset();
  };

  return (
    <Box>
      <Typography variant="h1" component="h1">
        Salary history
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
        Every pay change across the organisation
      </Typography>

      <Card sx={{ mb: 3, p: 2 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "1.4fr 1.4fr 1fr 1fr 1fr auto",
            },
            gap: 2,
            alignItems: "end",
          }}
        >
          <TextField
            label="Search employee"
            placeholder="Name or email"
            value={employeeInput}
            onChange={(event) => setEmployeeInput(event.target.value)}
            inputProps={{ maxLength: 100 }}
          />
          <TextField
            label="Search reason"
            placeholder="Search reason"
            value={reasonInput}
            onChange={(event) => setReasonInput(event.target.value)}
            inputProps={{ maxLength: 100 }}
          />
          <TextField
            select
            label="Change type"
            value={values.change_type}
            onChange={(event) => applyFilter("change_type", event.target.value)}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="hire">Hire</MenuItem>
            <MenuItem value="manual_edit">Manual edit</MenuItem>
            <MenuItem value="bulk_update">Bulk update</MenuItem>
          </TextField>
          <TextField
            label="From"
            type="date"
            value={values.date_from}
            onChange={(event) => applyFilter("date_from", event.target.value)}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="To"
            type="date"
            value={values.date_to}
            onChange={(event) => applyFilter("date_to", event.target.value)}
            InputLabelProps={{ shrink: true }}
          />
          <Button onClick={clearFilters}>Clear filters</Button>
        </Box>
      </Card>

      {values.batch_id ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Active filters:
          </Typography>
          <Chip
            size="small"
            label={`Batch ${values.batch_id.slice(0, 6)}`}
            onDelete={() => applyFilter("batch_id", "")}
            sx={{
              bgcolor: "#E6F4F1",
              color: "#0F766E",
              fontWeight: 600,
              "& .MuiChip-deleteIcon": { color: "#0F766E" },
            }}
          />
        </Box>
      ) : null}

      {historyQueryResult.isError ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => historyQueryResult.refetch()}>
              Retry
            </Button>
          }
        >
          Could not load salary history
        </Alert>
      ) : (
        <Card>
          <DataGrid
            rows={historyQueryResult.data?.items ?? []}
            columns={columns}
            rowCount={historyQueryResult.data?.total ?? 0}
            loading={historyQueryResult.isFetching}
            paginationMode="server"
            sortingMode="server"
            sortingOrder={["asc", "desc"]}
            paginationModel={{ page: page - 1, pageSize }}
            pageSizeOptions={[25, 50, 100]}
            sortModel={[{ field: sortBy, sort: sortDir }]}
            onPaginationModelChange={(model) => {
              const nextPage = model.pageSize !== pageSize ? 1 : model.page + 1;
              update({ page: String(nextPage), page_size: String(model.pageSize) });
            }}
            onSortModelChange={(model) => {
              const [sort] = model;
              if (!sort) {
                update({
                  sort_by: DEFAULT_STATE.sort_by,
                  sort_dir: DEFAULT_STATE.sort_dir,
                  page: "1",
                });
              } else if (sort.field !== sortBy || sort.sort !== sortDir) {
                update({ sort_by: sort.field, sort_dir: sort.sort, page: "1" });
              }
            }}
            onRowClick={(params) => navigate(`/employees/${params.row.employee.id}`)}
            rowHeight={60}
            columnHeaderHeight={44}
            disableColumnMenu
            sx={{
              border: 0,
              "& .MuiDataGrid-columnHeaders": { bgcolor: "#F1F4F9" },
              "& .MuiDataGrid-row:hover": { bgcolor: "#F8FAFD" },
            }}
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ p: 3, textAlign: "center" }}>
                  <Typography color="text.secondary">No changes match your filters</Typography>
                  <Button onClick={clearFilters} sx={{ mt: 1 }}>
                    Clear filters
                  </Button>
                </Box>
              ),
            }}
          />
        </Card>
      )}
    </Box>
  );
}
