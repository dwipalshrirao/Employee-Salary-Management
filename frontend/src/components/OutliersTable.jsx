import { Box, Card, CardContent, Chip, Link as MuiLink, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { Link as RouterLink } from "react-router-dom";

import { formatUsd } from "../lib/money";

export const OUTLIER_RULE =
  "Paid more than 1.5x the average for the same job title and country (at least 5 peers)";

function formatRatio(value) {
  return `${Number(value)
    .toFixed(2)
    .replace(/\.?0+$/, "")}x`;
}

const columns = [
  {
    field: "full_name",
    headerName: "Employee",
    minWidth: 170,
    flex: 1.1,
    renderCell: (params) => (
      <MuiLink
        component={RouterLink}
        to={`/employees/${params.row.employee_id}`}
        sx={{ fontWeight: 500, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
      >
        {params.value}
      </MuiLink>
    ),
  },
  {
    field: "job_title",
    headerName: "Job title",
    minWidth: 210,
    flex: 1.4,
  },
  {
    field: "country",
    headerName: "Country",
    minWidth: 140,
    flex: 0.9,
  },
  {
    field: "amount_cents",
    headerName: "Compensation",
    type: "number",
    minWidth: 140,
    flex: 0.8,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "peer_avg_cents",
    headerName: "Peer average",
    type: "number",
    minWidth: 140,
    flex: 0.8,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "ratio",
    headerName: "Ratio",
    type: "number",
    minWidth: 100,
    flex: 0.5,
    headerAlign: "right",
    align: "right",
    renderCell: (params) => (
      <Chip
        size="small"
        label={formatRatio(params.value)}
        sx={
          params.value >= 1.8
            ? { bgcolor: "#99efe5", color: "#00201d", fontWeight: 600 }
            : { bgcolor: "primary.light", color: "primary.main", fontWeight: 600 }
        }
      />
    ),
  },
];

export default function OutliersTable({
  rows = [],
  total = 0,
  page = 1,
  pageSize = 25,
  loading = false,
  onPageChange = () => {},
  onPageSizeChange = () => {},
}) {
  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h2">Pay outliers</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {OUTLIER_RULE}
        </Typography>
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(row) => row.employee_id}
          loading={loading}
          autoHeight
          paginationMode="server"
          rowCount={total}
          paginationModel={{ page: page - 1, pageSize }}
          pageSizeOptions={[10, 25, 50]}
          onPaginationModelChange={(model) => {
            if (model.pageSize !== pageSize) {
              onPageSizeChange(model.pageSize);
            } else if (model.page !== page - 1) {
              onPageChange(model.page + 1);
            }
          }}
          disableColumnMenu
          disableRowSelectionOnClick
          rowHeight={44}
          columnHeaderHeight={44}
          sx={{
            border: 0,
            "& .MuiDataGrid-columnHeaders": { bgcolor: "#F1F4F9" },
            "& .MuiDataGrid-row:hover": { bgcolor: "#F8FAFD" },
          }}
          slots={{
            noRowsOverlay: () => (
              <Box sx={{ p: 3, textAlign: "center" }}>
                <Typography color="text.secondary">No pay outliers for these filters</Typography>
              </Box>
            ),
          }}
        />
      </CardContent>
    </Card>
  );
}
