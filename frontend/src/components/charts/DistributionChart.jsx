import {
  Box,
  Card,
  CardContent,
  Skeleton,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const BAND_COLORS = ["#C7D7FE", "#A9BFFB", "#8AA6F8", "#6B8DF5", "#4B72F0", "#2E58E8", "#1B3A8F"];

function DistributionTooltip({ active, payload, bands }) {
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
      {payload
        .filter((entry) => entry.value > 0)
        .map((entry) => {
          const index = Number(entry.dataKey.replace("band_", ""));
          const count = row.counts[index] ?? 0;
          const percent = row.headcount ? (count / row.headcount) * 100 : 0;
          return (
            <Typography key={entry.dataKey} variant="body2">
              {`${bands[index].label}: ${count.toLocaleString()} (${Number(percent.toFixed(1))}%)`}
            </Typography>
          );
        })}
    </Box>
  );
}

export function buildDistributionRows(groups) {
  return groups.map((group) => {
    const row = {
      key: group.key,
      name: group.name,
      headcount: group.headcount,
      counts: group.counts,
    };
    group.counts.forEach((count, index) => {
      row[`band_${index}`] = group.headcount ? (count / group.headcount) * 100 : 0;
    });
    return row;
  });
}

function chartSummary(groupBy, groups) {
  const label = groupBy === "country" ? "country" : "department";
  return `Salary distribution by ${label}. ${groups
    .map((group) => `${group.name}: ${group.headcount.toLocaleString()} employees`)
    .join("; ")}`;
}

export default function DistributionChart({
  bands,
  groups,
  groupBy,
  onGroupByChange,
  loading = false,
}) {
  const rows = buildDistributionRows(groups);

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            justifyContent: "space-between",
            gap: 2,
            mb: 2,
          }}
        >
          <Box>
            <Typography variant="h2">Salary distribution</Typography>
            <Typography variant="body2" color="text.secondary">
              Each bar shows the share of employees in each salary band
            </Typography>
          </Box>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={groupBy}
            onChange={(_, nextGroup) => {
              if (nextGroup) {
                onGroupByChange(nextGroup);
              }
            }}
            aria-label="Distribution grouping"
          >
            <ToggleButton value="department">By department</ToggleButton>
            <ToggleButton value="country">By country</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {loading ? (
          <Skeleton variant="rounded" height={340} />
        ) : rows.length === 0 ? (
          <Box sx={{ height: 340, display: "grid", placeItems: "center" }}>
            <Typography color="text.secondary">No distribution data for these filters</Typography>
          </Box>
        ) : (
          <>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, mb: 2 }}>
              {bands.map((band, index) => (
                <Box key={band.index} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: 0.5,
                      bgcolor: BAND_COLORS[index],
                    }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {band.label}
                  </Typography>
                </Box>
              ))}
            </Box>
            <Box
              role="img"
              aria-label={chartSummary(groupBy, groups)}
              sx={{ width: "100%", height: 340 }}
            >
              <ResponsiveContainer
                width="100%"
                height="100%"
                initialDimension={{ width: 600, height: 340 }}
              >
                <BarChart
                  data={rows}
                  layout="vertical"
                  margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
                >
                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    ticks={[0, 25, 50, 75, 100]}
                    tickFormatter={(value) => `${value}%`}
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} />
                  <Tooltip content={<DistributionTooltip bands={bands} />} />
                  {bands.map((band, index) => (
                    <Bar
                      key={band.index}
                      dataKey={`band_${band.index}`}
                      stackId="bands"
                      fill={BAND_COLORS[index]}
                      isAnimationActive={false}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}
