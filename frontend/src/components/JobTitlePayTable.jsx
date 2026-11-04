import { Box, Card, CardContent, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";

import { formatUsd } from "../lib/money";

const columns = [
  {
    field: "name",
    headerName: "Job title",
    minWidth: 220,
    flex: 1.4,
  },
  {
    field: "headcount",
    headerName: "Headcount",
    type: "number",
    minWidth: 120,
    flex: 0.7,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => value.toLocaleString(),
  },
  {
    field: "min_cents",
    headerName: "Minimum",
    type: "number",
    minWidth: 130,
    flex: 0.8,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "avg_cents",
    headerName: "Average",
    type: "number",
    minWidth: 130,
    flex: 0.8,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => formatUsd(value),
  },
  {
    field: "max_cents",
    headerName: "Maximum",
    type: "number",
    minWidth: 130,
    flex: 0.8,
    headerAlign: "right",
    align: "right",
    valueFormatter: (value) => formatUsd(value),
  },
];

export default function JobTitlePayTable({ rows, loading = false }) {
  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: 2,
            mb: 2,
          }}
        >
          <Box>
            <Typography variant="h2">Pay by job title</Typography>
            <Typography variant="body2" color="text.secondary">
              Standard distribution stats by corporate role
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            {rows.length.toLocaleString()} roles tracked
          </Typography>
        </Box>
        <DataGrid
          rows={rows}
          columns={columns}
          getRowId={(row) => row.key}
          loading={loading}
          autoHeight
          pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { page: 0, pageSize: 10 } } }}
          sortingOrder={["asc", "desc"]}
          disableColumnMenu
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
                <Typography color="text.secondary">No job-title data for these filters</Typography>
              </Box>
            ),
          }}
        />
      </CardContent>
    </Card>
  );
}
