import { Box, Card, CardContent, Skeleton, Typography } from "@mui/material";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { formatUsd, formatUsdCompact } from "../../lib/money";

const VISUALLY_HIDDEN = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0,
};

function AverageTooltip({ active, payload }) {
  if (!active || !payload?.length) {
    return null;
  }
  const row = payload[0].payload;
  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 1.5,
        boxShadow: "0 8px 24px rgba(26, 34, 48, 0.12)",
      }}
    >
      <Typography sx={{ fontWeight: 600 }}>{row.name}</Typography>
      <Typography variant="body2">{`Headcount: ${row.headcount.toLocaleString()}`}</Typography>
      <Typography variant="body2">{`Minimum: ${formatUsd(row.min_cents)}`}</Typography>
      <Typography variant="body2">{`Average: ${formatUsd(row.avg_cents)}`}</Typography>
      <Typography variant="body2">{`Maximum: ${formatUsd(row.max_cents)}`}</Typography>
    </Box>
  );
}

function chartSummary(title, rows) {
  const items = rows.map(
    (row) =>
      `${row.name}: headcount ${row.headcount}, average ${formatUsd(
        row.avg_cents,
      )}, minimum ${formatUsd(row.min_cents)}, maximum ${formatUsd(row.max_cents)}`,
  );
  return `${title}. ${items.join("; ")}`;
}

export default function AverageBarChart({
  title,
  subtitle,
  rows,
  dimension,
  loading = false,
  onSelect,
}) {
  const sortedRows = [...rows].sort((left, right) => right.avg_cents - left.avg_cents);
  const horizontal = dimension === "department";

  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="h2">{title}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {subtitle}
        </Typography>
        {loading ? (
          <Skeleton variant="rounded" height={300} />
        ) : sortedRows.length === 0 ? (
          <Box sx={{ height: 300, display: "grid", placeItems: "center" }}>
            <Typography color="text.secondary">No data for these filters</Typography>
          </Box>
        ) : (
          <>
            <Box
              role="img"
              aria-label={chartSummary(title, sortedRows)}
              sx={{ width: "100%", height: 300 }}
            >
              <ResponsiveContainer
                width="100%"
                height="100%"
                initialDimension={{ width: 600, height: 300 }}
              >
                {horizontal ? (
                  <BarChart
                    data={sortedRows}
                    layout="vertical"
                    margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
                  >
                    <CartesianGrid horizontal={false} stroke="#E3E7EE" />
                    <XAxis type="number" tickFormatter={formatUsdCompact} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} />
                    <Tooltip content={<AverageTooltip />} />
                    <Bar
                      dataKey="avg_cents"
                      fill="#1E4ED8"
                      radius={[0, 4, 4, 0]}
                      cursor="pointer"
                      isAnimationActive={false}
                      onClick={(data) => onSelect?.(data?.key ?? data?.payload?.key)}
                    />
                  </BarChart>
                ) : (
                  <BarChart data={sortedRows} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid vertical={false} stroke="#E3E7EE" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
                    <YAxis tickFormatter={formatUsdCompact} tick={{ fontSize: 11 }} width={64} />
                    <Tooltip content={<AverageTooltip />} />
                    <Bar
                      dataKey="avg_cents"
                      fill="#1E4ED8"
                      radius={[4, 4, 0, 0]}
                      cursor="pointer"
                      isAnimationActive={false}
                      onClick={(data) => onSelect?.(data?.key ?? data?.payload?.key)}
                    />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </Box>
            <Box sx={VISUALLY_HIDDEN}>
              {sortedRows.map((row) => (
                <button key={row.key} type="button" onClick={() => onSelect?.(row.key)}>
                  {`${row.name}: average ${formatUsd(row.avg_cents)}`}
                </button>
              ))}
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}
