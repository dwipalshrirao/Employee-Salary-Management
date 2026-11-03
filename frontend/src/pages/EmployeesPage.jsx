import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, MenuItem, TextField, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { listEmployees } from "../api/employees";
import EmployeeAutocomplete from "../components/EmployeeAutocomplete";
import StatusChip from "../components/StatusChip";
import { useDebounce } from "../hooks/useDebounce";
import { useLookups } from "../hooks/useLookups";
import { useUrlState } from "../hooks/useUrlState";
import { formatDate } from "../lib/format";
import { formatUsd } from "../lib/money";

const DEFAULT_STATE = {
  q: "",
  country_code: "",
  department_id: "",
  job_title_id: "",
  manager_id: "",
  status: "active",
  sort_by: "full_name",
  sort_dir: "asc",
  page: "1",
  page_size: "25",
};

const SORTABLE_FIELDS = new Set([
  "full_name",
  "email",
  "hire_date",
  "base_salary",
  "total_comp",
  "department",
  "job_title",
  "country",
]);

const columns = [
  {
    field: "full_name",
    headerName: "Name",
    minWidth: 170,
    flex: 1.2,
  },
  {
    field: "email",
    headerName: "Email",
    minWidth: 220,
    flex: 1.4,
  },
  {
    field: "department",
    headerName: "Department",
    minWidth: 140,
    flex: 1,
    valueGetter: (value) => value?.name,
  },
  {
    field: "job_title",
    headerName: "Job title",
    minWidth: 180,
    flex: 1.2,
    valueGetter: (value) => value?.name,
  },
  {
    field: "country",
    headerName: "Country",
    minWidth: 130,
    flex: 0.9,
    valueGetter: (value) => value?.name,
  },
  {
    field: "manager",
    headerName: "Manager",
    minWidth: 150,
    flex: 1,
    sortable: false,
    valueGetter: (value) => value?.full_name ?? "—",
  },
  {
    field: "hire_date",
    headerName: "Hire date",
    minWidth: 120,
    valueGetter: (value) => formatDate(value),
  },
  {
    field: "base_salary",
    headerName: "Base salary",
    minWidth: 130,
    type: "number",
    headerAlign: "right",
    align: "right",
    valueGetter: (_, row) => row.base_salary_cents,
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "total_comp",
    headerName: "Total compensation",
    minWidth: 170,
    type: "number",
    headerAlign: "right",
    align: "right",
    valueGetter: (_, row) => row.total_comp_cents,
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "status",
    headerName: "Status",
    minWidth: 110,
    sortable: false,
    align: "center",
    headerAlign: "center",
    renderCell: (params) => <StatusChip status={params.value} />,
  },
];

function numberParam(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function employeeQuery(values) {
  const query = {
    status: values.status || DEFAULT_STATE.status,
    sort_by: SORTABLE_FIELDS.has(values.sort_by) ? values.sort_by : DEFAULT_STATE.sort_by,
    sort_dir: values.sort_dir === "desc" ? "desc" : "asc",
    page: numberParam(values.page, 1),
    page_size: numberParam(values.page_size, 25),
  };
  for (const key of ["q", "country_code", "department_id", "job_title_id", "manager_id"]) {
    if (values[key]) {
      query[key] = values[key];
    }
  }
  return query;
}

export default function EmployeesPage() {
  const navigate = useNavigate();
  const { values, update, reset } = useUrlState(DEFAULT_STATE);
  const [searchInput, setSearchInput] = useState(values.q);
  const debouncedSearch = useDebounce(searchInput, 300);
  const lookupsQuery = useLookups();
  const query = employeeQuery(values);
  const employeesQuery = useQuery({
    queryKey: ["employees", query],
    queryFn: () => listEmployees(query),
    placeholderData: keepPreviousData,
  });

  useEffect(() => {
    setSearchInput(values.q);
  }, [values.q]);

  useEffect(() => {
    if (debouncedSearch === searchInput && debouncedSearch !== values.q) {
      update({ q: debouncedSearch, page: "1" });
    }
  }, [debouncedSearch, searchInput, update, values.q]);

  const countries = lookupsQuery.data?.countries ?? [];
  const departments = lookupsQuery.data?.departments ?? [];
  const jobTitles = lookupsQuery.data?.job_titles ?? [];
  const pageSize = numberParam(values.page_size, 25);
  const page = numberParam(values.page, 1);
  const sortBy = SORTABLE_FIELDS.has(values.sort_by) ? values.sort_by : "full_name";
  const sortDir = values.sort_dir === "desc" ? "desc" : "asc";

  const applyFilter = (key, value) => update({ [key]: value, page: "1" });
  const clearFilters = () => {
    setSearchInput("");
    reset();
  };
  const retry = () => employeesQuery.refetch();

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5 }}>
          <Typography variant="h1" component="h1">
            Employees
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {employeesQuery.data ? `${employeesQuery.data.total.toLocaleString()} employees` : ""}
          </Typography>
        </Box>
        <Button component={Link} to="/employees/new" variant="contained">
          Add employee
        </Button>
      </Box>

      <Card sx={{ mt: 3, mb: 3, p: 2 }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "1.5fr repeat(3, minmax(0, 1fr)) 1.2fr 1fr auto",
            },
            gap: 2,
            alignItems: "end",
          }}
        >
          <TextField
            label="Search"
            placeholder="Search name or email"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
          <TextField
            select
            label="Country"
            value={lookupsQuery.data ? values.country_code : ""}
            onChange={(event) => applyFilter("country_code", event.target.value)}
          >
            <MenuItem value="">All countries</MenuItem>
            {countries.map((country) => (
              <MenuItem key={country.code} value={country.code}>
                {country.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Department"
            value={lookupsQuery.data ? values.department_id : ""}
            onChange={(event) => applyFilter("department_id", event.target.value)}
          >
            <MenuItem value="">All departments</MenuItem>
            {departments.map((department) => (
              <MenuItem key={department.id} value={department.id}>
                {department.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Job title"
            value={lookupsQuery.data ? values.job_title_id : ""}
            onChange={(event) => applyFilter("job_title_id", event.target.value)}
          >
            <MenuItem value="">All job titles</MenuItem>
            {jobTitles.map((jobTitle) => (
              <MenuItem key={jobTitle.id} value={jobTitle.id}>
                {jobTitle.name}
              </MenuItem>
            ))}
          </TextField>
          <EmployeeAutocomplete
            value={values.manager_id}
            onChange={(managerId) => applyFilter("manager_id", managerId)}
          />
          <TextField
            select
            label="Status"
            value={values.status || DEFAULT_STATE.status}
            onChange={(event) => applyFilter("status", event.target.value)}
          >
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
            <MenuItem value="all">All</MenuItem>
          </TextField>
          <Button onClick={clearFilters}>Clear filters</Button>
        </Box>
      </Card>

      {employeesQuery.isError ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={retry}>
              Retry
            </Button>
          }
        >
          Could not load employees
        </Alert>
      ) : (
        <Card>
          <DataGrid
            rows={employeesQuery.data?.items ?? []}
            columns={columns}
            rowCount={employeesQuery.data?.total ?? 0}
            loading={employeesQuery.isFetching}
            paginationMode="server"
            sortingMode="server"
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
                update({ sort_by: "full_name", sort_dir: "asc", page: "1" });
              } else if (sort.field !== sortBy || sort.sort !== sortDir) {
                update({ sort_by: sort.field, sort_dir: sort.sort, page: "1" });
              }
            }}
            onRowClick={(params) => navigate(`/employees/${params.id}`)}
            getRowClassName={(params) => (params.row.status === "inactive" ? "inactive-row" : "")}
            rowHeight={44}
            columnHeaderHeight={44}
            disableColumnMenu
            sx={{
              border: 0,
              "& .MuiDataGrid-columnHeaders": { bgcolor: "#F1F4F9" },
              "& .MuiDataGrid-row:hover": { bgcolor: "#F8FAFD" },
              "& .MuiDataGrid-row.inactive-row": { color: "text.secondary" },
            }}
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ p: 3, textAlign: "center" }}>
                  <Typography color="text.secondary">No employees match your filters</Typography>
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
