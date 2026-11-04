import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  InputAdornment,
  MenuItem,
  Radio,
  RadioGroup,
  Step,
  StepLabel,
  Stepper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink } from "react-router-dom";

import { ApiError } from "../api/client";
import { applyBulkUpdate, previewBulkUpdate } from "../api/bulk";
import EmployeeAutocomplete from "../components/EmployeeAutocomplete";
import { useLookups } from "../hooks/useLookups";
import { formatUsd, parseDollarsToCents } from "../lib/money";
import { bulkUpdateFormSchema } from "../lib/schemas";

const DEFAULT_VALUES = {
  country_code: "",
  department_id: "",
  job_title_id: "",
  manager_id: "",
  component: "base",
  mode: "percent",
  value: "",
  reason: "",
  apply_to_all: false,
};

const COMPONENT_LABELS = {
  base: "base salary",
  bonus: "bonus",
  allowances: "allowances",
};

const COMPONENT_TITLES = {
  base: "Base salary",
  bonus: "Bonus",
  allowances: "Allowances",
};

function buildPreviewBody(values) {
  const filter = {
    country_code: values.country_code || null,
    department_id: values.department_id ? Number(values.department_id) : null,
    job_title_id: values.job_title_id ? Number(values.job_title_id) : null,
    manager_id: values.manager_id ? Number(values.manager_id) : null,
  };
  const body = {
    filter,
    apply_to_all: values.apply_to_all,
    component: values.component,
    mode: values.mode,
  };
  if (values.mode === "percent") {
    body.percentage = values.value.trim();
  } else {
    body.amount_cents = parseDollarsToCents(values.value);
  }
  return body;
}

function percentLabel(value) {
  const number = Number(value);
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function describeFilters(values, lookups) {
  const parts = [];
  if (values.country_code) {
    const country = lookups.data?.countries.find((item) => item.code === values.country_code);
    parts.push(country?.name ?? values.country_code);
  }
  if (values.department_id) {
    const department = lookups.data?.departments.find(
      (item) => String(item.id) === values.department_id,
    );
    parts.push(department?.name ?? `Department ${values.department_id}`);
  }
  if (values.job_title_id) {
    const title = lookups.data?.job_titles.find((item) => String(item.id) === values.job_title_id);
    parts.push(title?.name ?? `Job title ${values.job_title_id}`);
  }
  if (values.manager_id) {
    parts.push("selected manager");
  }
  return parts.length ? parts.join(", ") : "all active employees";
}

function employeeListLink(filter) {
  const params = new URLSearchParams();
  for (const key of ["country_code", "department_id", "job_title_id", "manager_id"]) {
    if (filter?.[key]) {
      params.set(key, String(filter[key]));
    }
  }
  const query = params.toString();
  return query ? `/employees?${query}` : "/employees";
}

export default function BulkUpdatePage() {
  const queryClient = useQueryClient();
  const lookups = useLookups();
  const [activeStep, setActiveStep] = useState(0);
  const [preview, setPreview] = useState(null);
  const [previewBody, setPreviewBody] = useState(null);
  const [targetError, setTargetError] = useState("");
  const [applyError, setApplyError] = useState("");
  const [staleWarning, setStaleWarning] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [result, setResult] = useState(null);
  const {
    control,
    register,
    handleSubmit,
    watch,
    reset,
    getValues,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(bulkUpdateFormSchema),
    defaultValues: DEFAULT_VALUES,
  });
  const values = watch();
  const previewMutation = useMutation({ mutationFn: previewBulkUpdate });
  const applyMutation = useMutation({ mutationFn: applyBulkUpdate });
  const componentLabel = COMPONENT_LABELS[values.component];
  const componentTitle = COMPONENT_TITLES[values.component];

  async function submitPreview(formValues) {
    setTargetError("");
    setStaleWarning("");
    const body = buildPreviewBody(formValues);
    try {
      const data = await previewMutation.mutateAsync(body);
      setPreview(data);
      setPreviewBody(body);
      setActiveStep(1);
    } catch (caught) {
      setTargetError(caught.message || "Could not preview this update");
    }
  }

  async function refreshStalePreview() {
    try {
      const data = await previewMutation.mutateAsync(previewBody);
      setPreview(data);
    } catch (caught) {
      setTargetError(caught.message || "Could not refresh the preview");
      setActiveStep(0);
    }
  }

  async function confirmApply() {
    setApplyError("");
    try {
      const data = await applyMutation.mutateAsync({
        ...previewBody,
        expected_count: preview.affected_count,
        reason: getValues("reason").trim(),
      });
      setResult(data);
      setConfirmOpen(false);
      setActiveStep(3);
      for (const queryKey of [["employees"], ["employee"], ["history"], ["analytics"]]) {
        queryClient.invalidateQueries({ queryKey });
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "stale_preview") {
        setConfirmOpen(false);
        setActiveStep(1);
        setStaleWarning(caught.message);
        await refreshStalePreview();
        return;
      }
      if (caught instanceof ApiError && caught.code === "result_too_large") {
        setConfirmOpen(false);
        setActiveStep(0);
        setTargetError(caught.message);
        return;
      }
      setApplyError(caught.message || "Could not apply this update");
    }
  }

  function startAnotherUpdate() {
    reset(DEFAULT_VALUES);
    setPreview(null);
    setPreviewBody(null);
    setResult(null);
    setTargetError("");
    setApplyError("");
    setStaleWarning("");
    setActiveStep(0);
  }

  return (
    <Box sx={{ maxWidth: 1080, mx: "auto" }}>
      <Typography variant="h1" component="h1">
        Bulk pay update
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
        Apply calculated compensation changes across employee cohorts
      </Typography>

      <Stepper activeStep={result ? 3 : activeStep} alternativeLabel sx={{ mb: 4 }}>
        {["Target", "Preview", "Confirm"].map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {targetError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {targetError}
        </Alert>
      ) : null}

      {result ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          <Alert severity="success">
            <Typography
              sx={{ fontWeight: 600 }}
            >{`Updated ${result.affected_count} employees`}</Typography>
            <Typography>{`${componentTitle} changed by ${formatUsd(
              result.sum_delta_cents,
            )} annually.`}</Typography>
          </Alert>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h2" sx={{ mb: 2 }}>
                Transaction summary
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: { md: "1fr 1fr 1fr" }, gap: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Component
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{componentTitle}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Employees affected
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{result.affected_count}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Batch
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{result.batch_id.slice(0, 8)}</Typography>
                </Box>
              </Box>
              <Box sx={{ display: "flex", gap: 2, mt: 3 }}>
                <Button
                  component={RouterLink}
                  to={employeeListLink(previewBody?.filter)}
                  variant="outlined"
                >
                  View in employee list
                </Button>
                <Button
                  component={RouterLink}
                  to={`/history?batch_id=${result.batch_id}`}
                  variant="outlined"
                >
                  View changes in history
                </Button>
              </Box>
            </CardContent>
          </Card>
          <Box>
            <Button onClick={startAnotherUpdate}>Start another update</Button>
          </Box>
        </Box>
      ) : activeStep === 0 ? (
        <Card>
          <CardContent sx={{ p: 4 }}>
            <Box component="form" onSubmit={handleSubmit(submitPreview)} noValidate>
              <Typography variant="h2" sx={{ mb: 2 }}>
                Target
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
                  gap: 2,
                }}
              >
                <Controller
                  name="country_code"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} select label="Country" fullWidth>
                      <MenuItem value="">All countries</MenuItem>
                      {(lookups.data?.countries ?? []).map((country) => (
                        <MenuItem key={country.code} value={country.code}>
                          {country.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
                <Controller
                  name="department_id"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} select label="Department" fullWidth>
                      <MenuItem value="">All departments</MenuItem>
                      {(lookups.data?.departments ?? []).map((department) => (
                        <MenuItem key={department.id} value={String(department.id)}>
                          {department.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
                <Controller
                  name="job_title_id"
                  control={control}
                  render={({ field }) => (
                    <TextField {...field} select label="Job title" fullWidth>
                      <MenuItem value="">All job titles</MenuItem>
                      {(lookups.data?.job_titles ?? []).map((jobTitle) => (
                        <MenuItem key={jobTitle.id} value={String(jobTitle.id)}>
                          {jobTitle.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
                <Controller
                  name="manager_id"
                  control={control}
                  render={({ field }) => (
                    <EmployeeAutocomplete value={field.value} onChange={field.onChange} />
                  )}
                />
              </Box>

              <Box sx={{ display: "grid", gridTemplateColumns: { md: "1fr 1fr" }, gap: 3, mt: 3 }}>
                <FormControl>
                  <FormLabel>What to change</FormLabel>
                  <Controller
                    name="component"
                    control={control}
                    render={({ field }) => (
                      <RadioGroup row {...field}>
                        <FormControlLabel value="base" control={<Radio />} label="Base salary" />
                        <FormControlLabel value="bonus" control={<Radio />} label="Bonus" />
                        <FormControlLabel
                          value="allowances"
                          control={<Radio />}
                          label="Allowances"
                        />
                      </RadioGroup>
                    )}
                  />
                </FormControl>
                <FormControl>
                  <FormLabel>How</FormLabel>
                  <Controller
                    name="mode"
                    control={control}
                    render={({ field }) => (
                      <RadioGroup row {...field}>
                        <FormControlLabel
                          value="percent"
                          control={<Radio />}
                          label="Percentage change"
                        />
                        <FormControlLabel
                          value="fixed_amount"
                          control={<Radio />}
                          label="Add fixed amount"
                        />
                      </RadioGroup>
                    )}
                  />
                </FormControl>
              </Box>

              <Box sx={{ display: "grid", gridTemplateColumns: { md: "1fr 1fr" }, gap: 2, mt: 3 }}>
                <TextField
                  label="Adjustment value"
                  error={Boolean(errors.value)}
                  helperText={
                    errors.value?.message ??
                    (values.mode === "percent"
                      ? "Between -50% and +100%"
                      : "Annual amount in USD. For $100 per month, enter $1,200.")
                  }
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        {values.mode === "percent" ? "%" : "$"}
                      </InputAdornment>
                    ),
                  }}
                  {...register("value")}
                />
                <TextField
                  label="Reason"
                  error={Boolean(errors.reason)}
                  helperText={errors.reason?.message}
                  {...register("reason")}
                />
              </Box>

              <Controller
                name="apply_to_all"
                control={control}
                render={({ field }) => (
                  <FormControl error={Boolean(errors.apply_to_all)} sx={{ mt: 2 }}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={field.value}
                          onChange={(event) => field.onChange(event.target.checked)}
                        />
                      }
                      label="Apply to all active employees"
                    />
                    {errors.apply_to_all ? (
                      <Typography variant="caption" color="error">
                        {errors.apply_to_all.message}
                      </Typography>
                    ) : null}
                  </FormControl>
                )}
              />

              {values.apply_to_all ? (
                <Alert severity="warning" sx={{ mt: 2 }}>
                  Organization-wide update will affect all active employees across all regions.
                </Alert>
              ) : null}

              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
                Changes apply immediately and update the current annual amount. One-off or monthly
                payments are not supported.
              </Typography>

              <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
                <Button type="submit" variant="contained" disabled={previewMutation.isPending}>
                  {previewMutation.isPending ? "Previewing…" : "Preview"}
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {staleWarning ? (
            <Alert severity="warning">{staleWarning} A fresh preview has been generated.</Alert>
          ) : null}
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
                <Typography sx={{ fontWeight: 600 }}>
                  {`Targeting: ${describeFilters(values, lookups)}, ${componentTitle}: ${
                    values.mode === "percent"
                      ? percentLabel(values.value)
                      : `+${formatUsd(parseDollarsToCents(values.value))}`
                  }`}
                </Typography>
                <Typography color="text.secondary">{values.reason}</Typography>
              </Box>
            </CardContent>
          </Card>

          <Box sx={{ display: "grid", gridTemplateColumns: { md: "repeat(4, 1fr)" }, gap: 2 }}>
            {[
              ["Employees affected", preview.affected_count],
              [`Total ${componentLabel} before`, formatUsd(preview.sum_before_cents)],
              [`Total ${componentLabel} after`, formatUsd(preview.sum_after_cents)],
              ["Difference", formatUsd(preview.sum_delta_cents)],
            ].map(([label, value]) => (
              <Card key={label}>
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography variant="h2">{value}</Typography>
                </CardContent>
              </Card>
            ))}
          </Box>

          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h2" sx={{ mb: 2 }}>
                Sample preview records
              </Typography>
              {preview.sample.length === 0 ? (
                <Typography color="text.secondary">No employees would change</Typography>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell align="right">{componentTitle} before</TableCell>
                      <TableCell align="right">{componentTitle} after</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {preview.sample.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.full_name}</TableCell>
                        <TableCell align="right">{formatUsd(row.before_cents)}</TableCell>
                        <TableCell align="right">{formatUsd(row.after_cents)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          <Box sx={{ display: "flex", justifyContent: "space-between" }}>
            <Button onClick={() => setActiveStep(0)}>Back</Button>
            <Button
              variant="contained"
              disabled={preview.affected_count === 0 || previewMutation.isPending}
              onClick={() => {
                setApplyError("");
                setActiveStep(2);
                setConfirmOpen(true);
              }}
            >
              Continue
            </Button>
          </Box>
        </Box>
      )}

      <Dialog
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setActiveStep(1);
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Apply this change?</DialogTitle>
        <DialogContent>
          {applyError ? (
            <Alert severity="error" sx={{ mb: 2 }}>
              {applyError}
            </Alert>
          ) : null}
          <DialogContentText>
            {values.mode === "percent"
              ? `Apply ${percentLabel(values.value)} to the ${componentLabel} of ${preview?.affected_count ?? 0} employees.`
              : `Add ${formatUsd(parseDollarsToCents(values.value || "0"))} per year to the ${componentLabel} of ${preview?.affected_count ?? 0} employees.`}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setConfirmOpen(false);
              setApplyError("");
              setActiveStep(1);
            }}
            disabled={applyMutation.isPending}
          >
            Cancel
          </Button>
          <Button variant="contained" onClick={confirmApply} disabled={applyMutation.isPending}>
            {applyMutation.isPending
              ? "Applying…"
              : `Apply to ${preview?.affected_count ?? 0} employees`}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
