import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  MenuItem,
  Skeleton,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  getAnalyticsBreakdown,
  getAnalyticsDistribution,
  getAnalyticsSummary,
} from "../api/analytics";
import JobTitlePayTable from "../components/JobTitlePayTable";
import StatCard from "../components/StatCard";
import AverageBarChart from "../components/charts/AverageBarChart";
import DistributionChart from "../components/charts/DistributionChart";
import { useLookups } from "../hooks/useLookups";
import { useUrlState } from "../hooks/useUrlState";
import { formatUsd, formatUsdCompact } from "../lib/money";

const DEFAULT_STATE = {
  measure: "total",
  country_code: "",
  department_id: "",
};

const MEASURE_LABELS = {
  total: "Total compensation",
  base: "Base salary",
};

const PAY_COMPONENTS = [
  { key: "base_cents", label: "Base", color: "#1E4ED8" },
  { key: "bonus_cents", label: "Bonus", color: "#0F766E" },
  { key: "allowances_cents", label: "Allowances", color: "#B45309" },
];

function filtersFor(values) {
  const filters = {
    measure: values.measure === "base" ? "base" : "total",
  };
  if (values.country_code) {
    filters.country_code = values.country_code;
  }
  if (values.department_id) {
    filters.department_id = values.department_id;
  }
  return filters;
}

function highestCountry(rows) {
  return [...rows].sort((left, right) => right.avg_cents - left.avg_cents)[0];
}

function PayMix({ summary, loading }) {
  if (loading) {
    return <Skeleton variant="rounded" height={76} />;
  }
  const components = summary?.components;
  const total = components
    ? components.base_cents + components.bonus_cents + components.allowances_cents
    : 0;
  if (!components || total === 0) {
    return <Typography color="text.secondary">No compensation data for these filters</Typography>;
  }

  const parts = PAY_COMPONENTS.map((component) => ({
    ...component,
    cents: components[component.key],
    percent: Math.round((components[component.key] / total) * 100),
  }));

  return (
    <Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2.5, mb: 2 }}>
        {parts.map((part) => (
          <Box key={part.key} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: 1, bgcolor: part.color }} />
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {part.label}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {`${part.percent}% · ${formatUsdCompact(part.cents)}`}
            </Typography>
          </Box>
        ))}
      </Box>
      <Box
        role="img"
        aria-label={parts
          .map((part) => `${part.label} ${part.percent} percent, ${formatUsd(part.cents)}`)
          .join("; ")}
        sx={{ display: "flex", height: 36, borderRadius: 1, overflow: "hidden" }}
      >
        {parts
          .filter((part) => part.percent > 0)
          .map((part) => (
            <Box
              key={part.key}
              sx={{
                width: `${part.percent}%`,
                bgcolor: part.color,
                color: "#FFFFFF",
                display: "grid",
                placeItems: "center",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {part.percent >= 8 ? `${part.percent}%` : ""}
            </Box>
          ))}
      </Box>
    </Box>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { values, update } = useUrlState(DEFAULT_STATE);
  const [distributionGroup, setDistributionGroup] = useState("department");
  const lookups = useLookups();
  const filters = filtersFor(values);
  const summaryQuery = useQuery({
    queryKey: ["analytics", "summary", filters],
    queryFn: () => getAnalyticsSummary(filters),
    staleTime: 60_000,
  });
  const countryQuery = useQuery({
    queryKey: ["analytics", "breakdown", "country", filters],
    queryFn: () => getAnalyticsBreakdown({ ...filters, group_by: "country" }),
    staleTime: 60_000,
  });
  const departmentQuery = useQuery({
    queryKey: ["analytics", "breakdown", "department", filters],
    queryFn: () => getAnalyticsBreakdown({ ...filters, group_by: "department" }),
    staleTime: 60_000,
  });
  const jobTitleQuery = useQuery({
    queryKey: ["analytics", "breakdown", "job_title", filters],
    queryFn: () => getAnalyticsBreakdown({ ...filters, group_by: "job_title" }),
    staleTime: 60_000,
  });
  const distributionQuery = useQuery({
    queryKey: ["analytics", "distribution", distributionGroup, filters],
    queryFn: () => getAnalyticsDistribution({ ...filters, group_by: distributionGroup }),
    staleTime: 60_000,
  });

  const retry = () => {
    summaryQuery.refetch();
    countryQuery.refetch();
    departmentQuery.refetch();
    jobTitleQuery.refetch();
    distributionQuery.refetch();
  };

  const measure = filters.measure;
  const summary = summaryQuery.data;
  const countryRows = countryQuery.data?.rows ?? [];
  const departmentRows = departmentQuery.data?.rows ?? [];
  const jobTitleRows = jobTitleQuery.data?.rows ?? [];
  const topCountry = highestCountry(countryRows);
  const hasError =
    summaryQuery.isError ||
    countryQuery.isError ||
    departmentQuery.isError ||
    jobTitleQuery.isError ||
    distributionQuery.isError;
  const countries = lookups.data?.countries ?? [];
  const departments = lookups.data?.departments ?? [];

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", lg: "row" },
          alignItems: { lg: "center" },
          justifyContent: "space-between",
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography variant="h1" component="h1">
            Pay insights
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Active employees only
          </Typography>
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, alignItems: "center" }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={measure}
            onChange={(_, nextMeasure) => {
              if (nextMeasure) {
                update({ measure: nextMeasure });
              }
            }}
            aria-label="Measure"
          >
            <ToggleButton value="total">Total compensation</ToggleButton>
            <ToggleButton value="base">Base salary</ToggleButton>
          </ToggleButtonGroup>
          <TextField
            select
            label="Country"
            value={lookups.data ? values.country_code : ""}
            onChange={(event) => update({ country_code: event.target.value })}
            sx={{ minWidth: 180 }}
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
            value={lookups.data ? values.department_id : ""}
            onChange={(event) => update({ department_id: event.target.value })}
            sx={{ minWidth: 190 }}
          >
            <MenuItem value="">All departments</MenuItem>
            {departments.map((department) => (
              <MenuItem key={department.id} value={String(department.id)}>
                {department.name}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      </Box>

      {hasError ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={retry}>
              Retry
            </Button>
          }
        >
          Could not load dashboard
        </Alert>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
              gap: 2,
            }}
          >
            <StatCard
              title="Total compensation expenditure"
              value={summary ? formatUsdCompact(summary.total_cents) : ""}
              subtitle={MEASURE_LABELS[measure]}
              loading={summaryQuery.isLoading}
            />
            <StatCard
              title="Headcount"
              value={summary ? summary.headcount.toLocaleString() : ""}
              subtitle="Active employees"
              loading={summaryQuery.isLoading}
            />
            <StatCard
              title="Average compensation"
              value={summary ? formatUsd(summary.avg_cents) : ""}
              subtitle={MEASURE_LABELS[measure]}
              loading={summaryQuery.isLoading}
            />
            <StatCard
              title="Highest-paying country"
              value={topCountry?.name ?? "No data"}
              subtitle={
                topCountry
                  ? `${formatUsd(topCountry.avg_cents)} average`
                  : "No employees match these filters"
              }
              loading={countryQuery.isLoading}
            />
          </Box>

          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h2">Pay mix</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Base, bonus and allowances share
              </Typography>
              <PayMix summary={summary} loading={summaryQuery.isLoading} />
            </CardContent>
          </Card>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
              gap: 2,
            }}
          >
            <AverageBarChart
              title="Average compensation by country"
              subtitle="Sorted high to low across countries"
              rows={countryRows}
              dimension="country"
              loading={countryQuery.isLoading}
              onSelect={(key) => navigate(`/employees?country_code=${encodeURIComponent(key)}`)}
            />
            <AverageBarChart
              title="Average compensation by department"
              subtitle="Ranked by average compensation"
              rows={departmentRows}
              dimension="department"
              loading={departmentQuery.isLoading}
              onSelect={(key) => navigate(`/employees?department_id=${encodeURIComponent(key)}`)}
            />
          </Box>

          <DistributionChart
            bands={distributionQuery.data?.bands ?? []}
            groups={distributionQuery.data?.groups ?? []}
            groupBy={distributionGroup}
            onGroupByChange={setDistributionGroup}
            loading={distributionQuery.isLoading}
          />

          <JobTitlePayTable rows={jobTitleRows} loading={jobTitleQuery.isLoading} />
        </Box>
      )}
    </Box>
  );
}
