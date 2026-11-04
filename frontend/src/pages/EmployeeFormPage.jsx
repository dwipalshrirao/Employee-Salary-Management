import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  InputAdornment,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { createEmployee, getEmployee, updateEmployee } from "../api/employees";
import EmployeeAutocomplete from "../components/EmployeeAutocomplete";
import { useLookups } from "../hooks/useLookups";
import { employeeFormSchema } from "../lib/schemas";
import { centsToDollarsString, formatLocal, formatUsd, parseDollarsToCents } from "../lib/money";

const DEFAULT_VALUES = {
  full_name: "",
  email: "",
  department_id: "",
  job_title_id: "",
  country_code: "",
  manager_id: "",
  hire_date: "",
  base_salary: "",
  bonus_cents: "",
  allowances_cents: "",
  change_reason: "",
};

function formValuesFor(employee) {
  return {
    full_name: employee.full_name,
    email: employee.email,
    department_id: String(employee.department.id),
    job_title_id: String(employee.job_title.id),
    country_code: employee.country.code,
    manager_id: employee.manager ? String(employee.manager.id) : "",
    hire_date: employee.hire_date,
    base_salary: centsToDollarsString(employee.base_salary_cents),
    bonus_cents: centsToDollarsString(employee.bonus_cents),
    allowances_cents: centsToDollarsString(employee.allowances_cents),
    change_reason: "",
  };
}

function editPatchFor(values, employee) {
  const patch = {};
  if (values.full_name.trim() !== employee.full_name) {
    patch.full_name = values.full_name.trim();
  }
  if (values.email.trim() !== employee.email) {
    patch.email = values.email.trim();
  }
  if (Number(values.department_id) !== employee.department.id) {
    patch.department_id = Number(values.department_id);
  }
  if (Number(values.job_title_id) !== employee.job_title.id) {
    patch.job_title_id = Number(values.job_title_id);
  }
  if (values.country_code !== employee.country.code) {
    patch.country_code = values.country_code;
  }
  const managerId = values.manager_id ? Number(values.manager_id) : null;
  if (managerId !== (employee.manager?.id ?? null)) {
    patch.manager_id = managerId;
  }
  if (values.hire_date !== employee.hire_date) {
    patch.hire_date = values.hire_date;
  }
  if (amountCents(values.base_salary) !== employee.base_salary_cents) {
    patch.base_salary_cents = amountCents(values.base_salary);
  }
  if (amountCents(values.bonus_cents) !== employee.bonus_cents) {
    patch.bonus_cents = amountCents(values.bonus_cents);
  }
  if (amountCents(values.allowances_cents) !== employee.allowances_cents) {
    patch.allowances_cents = amountCents(values.allowances_cents);
  }
  const payChanged = ["base_salary_cents", "bonus_cents", "allowances_cents"].some(
    (field) => field in patch,
  );
  if (payChanged && values.change_reason.trim()) {
    patch.change_reason = values.change_reason.trim();
  }
  return { patch, payChanged };
}

function amountCents(value) {
  if (!value?.trim()) {
    return 0;
  }
  try {
    return parseDollarsToCents(value);
  } catch {
    return 0;
  }
}

function FieldError({ message }) {
  return message ? (
    <Typography variant="caption" color="error" sx={{ display: "block", mt: 0.75 }}>
      {message}
    </Typography>
  ) : null;
}

export default function EmployeeFormPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const lookups = useLookups();
  const [serverError, setServerError] = useState("");
  const [discardOpen, setDiscardOpen] = useState(false);
  const pendingPath = useRef(null);
  const employeeQuery = useQuery({
    queryKey: ["employee", id],
    queryFn: () => getEmployee(id),
    retry: false,
    enabled: isEdit,
  });
  const employee = employeeQuery.data;
  const editValues = useMemo(() => (employee ? formValuesFor(employee) : undefined), [employee]);
  const {
    control,
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm({
    resolver: zodResolver(employeeFormSchema),
    defaultValues: DEFAULT_VALUES,
    values: isEdit ? editValues : undefined,
  });

  const watched = watch();
  const editState =
    isEdit && employee ? editPatchFor(watched, employee) : { patch: {}, payChanged: false };
  const hasChanges = isEdit ? Object.keys(editState.patch).length > 0 : isDirty;
  const cancelPath = isEdit ? `/employees/${id}` : "/employees";
  const countries = lookups.data?.countries ?? [];
  const departments = lookups.data?.departments ?? [];
  const jobTitles = lookups.data?.job_titles ?? [];
  const selectedCountry = countries.find((country) => country.code === watched.country_code);
  const currencyRate = lookups.data?.currency_rates.find(
    (rate) => rate.currency_code === selectedCountry?.currency_code,
  );
  const totalCents =
    amountCents(watched.base_salary) +
    amountCents(watched.bonus_cents) +
    amountCents(watched.allowances_cents);
  const localTotalCents =
    currencyRate && selectedCountry ? Math.round(totalCents * currencyRate.rate_per_usd) : null;

  async function onSubmit(values) {
    setServerError("");
    if (isEdit) {
      const { patch } = editPatchFor(values, employee);
      if (Object.keys(patch).length === 0) {
        return;
      }
      try {
        await updateEmployee(id, patch);
        await queryClient.invalidateQueries({ queryKey: ["employee", id] });
        await queryClient.invalidateQueries({ queryKey: ["employee", id, "history"] });
        await queryClient.invalidateQueries({ queryKey: ["employees"] });
        navigate(`/employees/${id}`);
      } catch (caught) {
        handleSubmitError(caught);
      }
      return;
    }

    const body = {
      full_name: values.full_name.trim(),
      email: values.email.trim(),
      department_id: Number(values.department_id),
      job_title_id: Number(values.job_title_id),
      country_code: values.country_code,
      hire_date: values.hire_date,
      base_salary_cents: parseDollarsToCents(values.base_salary),
      bonus_cents: amountCents(values.bonus_cents),
      allowances_cents: amountCents(values.allowances_cents),
    };
    if (values.manager_id) {
      body.manager_id = Number(values.manager_id);
    }

    try {
      const created = await createEmployee(body);
      await queryClient.invalidateQueries({ queryKey: ["employees"] });
      navigate(`/employees/${created.id}`);
    } catch (caught) {
      handleSubmitError(caught);
    }
  }

  function handleSubmitError(caught) {
    if (caught instanceof ApiError && caught.status === 409) {
      setError("email", {
        type: "server",
        message: caught.message || "Email already exists",
      });
      return;
    }
    if (caught instanceof ApiError && caught.status === 422) {
      let mapped = false;
      for (const [field, messages] of Object.entries(caught.details ?? {})) {
        if (field in DEFAULT_VALUES) {
          setError(field, {
            type: "server",
            message: Array.isArray(messages) ? messages[0] : String(messages),
          });
          mapped = true;
        }
      }
      if (mapped) {
        return;
      }
    }
    setServerError(caught.message || "Could not save employee");
  }

  function requestLeave(path) {
    if (hasChanges) {
      pendingPath.current = path;
      setDiscardOpen(true);
    } else {
      navigate(path);
    }
  }

  function discardChanges() {
    setDiscardOpen(false);
    navigate(pendingPath.current ?? cancelPath);
  }

  useEffect(() => {
    if (!hasChanges) {
      return undefined;
    }
    const handler = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [hasChanges]);

  if (isEdit && employeeQuery.isLoading) {
    return (
      <Box sx={{ minHeight: 320, display: "grid", placeItems: "center" }}>
        <CircularProgress aria-label="Loading employee" />
      </Box>
    );
  }

  if (isEdit && employeeQuery.isError) {
    return (
      <Alert severity="error" sx={{ maxWidth: 960, mx: "auto" }}>
        Could not load employee
      </Alert>
    );
  }

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <RouterLink
          to="/employees"
          style={{ color: "inherit", textDecoration: "none" }}
          onClick={(event) => {
            if (hasChanges) {
              event.preventDefault();
              requestLeave("/employees");
            }
          }}
        >
          Employees
        </RouterLink>
        <Typography color="text.disabled">/</Typography>
        <Typography sx={{ fontWeight: 600 }}>
          {isEdit ? (employee?.full_name ?? "Edit employee") : "New employee"}
        </Typography>
      </Box>
      <Typography variant="h1" component="h1" sx={{ mt: 1, mb: 3 }}>
        {isEdit ? "Edit employee" : "Add employee"}
      </Typography>

      {serverError ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {serverError}
        </Alert>
      ) : null}

      <Card>
        <CardContent sx={{ p: 4 }}>
          <Box component="form" noValidate onSubmit={handleSubmit(onSubmit)}>
            <Typography variant="h2" sx={{ pb: 1.5, borderBottom: 1, borderColor: "divider" }}>
              Personal and job
            </Typography>
            <Box
              sx={{
                mt: 2.5,
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                gap: 2.5,
              }}
            >
              <Box>
                <TextField
                  label="Full name"
                  fullWidth
                  error={Boolean(errors.full_name)}
                  {...register("full_name")}
                />
                <FieldError message={errors.full_name?.message} />
              </Box>
              <Box>
                <TextField
                  label="Email"
                  type="email"
                  fullWidth
                  error={Boolean(errors.email)}
                  helperText={errors.email?.message}
                  {...register("email")}
                />
              </Box>
              <Box>
                <Controller
                  name="department_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Department"
                      fullWidth
                      error={Boolean(errors.department_id)}
                      helperText={errors.department_id?.message}
                    >
                      <MenuItem value="">Select department</MenuItem>
                      {departments.map((department) => (
                        <MenuItem key={department.id} value={String(department.id)}>
                          {department.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Box>
              <Box>
                <Controller
                  name="job_title_id"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Job title"
                      fullWidth
                      error={Boolean(errors.job_title_id)}
                      helperText={errors.job_title_id?.message}
                    >
                      <MenuItem value="">Select job title</MenuItem>
                      {jobTitles.map((jobTitle) => (
                        <MenuItem key={jobTitle.id} value={String(jobTitle.id)}>
                          {jobTitle.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Box>
              <Box>
                <Controller
                  name="country_code"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      select
                      label="Country"
                      fullWidth
                      error={Boolean(errors.country_code)}
                      helperText={errors.country_code?.message}
                    >
                      <MenuItem value="">Select country</MenuItem>
                      {countries.map((country) => (
                        <MenuItem key={country.code} value={country.code}>
                          {country.name}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                />
              </Box>
              <Box>
                <Controller
                  name="manager_id"
                  control={control}
                  render={({ field }) => (
                    <EmployeeAutocomplete
                      label="Manager (optional)"
                      value={field.value}
                      onChange={field.onChange}
                      initialOption={employee?.manager ?? null}
                    />
                  )}
                />
              </Box>
              <Box>
                <TextField
                  label="Hire date"
                  type="date"
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  error={Boolean(errors.hire_date)}
                  helperText={errors.hire_date?.message}
                  {...register("hire_date")}
                />
              </Box>
            </Box>

            <Typography
              variant="h2"
              sx={{ mt: 4, pb: 1.5, borderBottom: 1, borderColor: "divider" }}
            >
              Compensation (annual, USD)
            </Typography>
            <Box
              sx={{
                mt: 2.5,
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" },
                gap: 2.5,
              }}
            >
              <Box>
                <TextField
                  label="Base salary"
                  fullWidth
                  error={Boolean(errors.base_salary)}
                  helperText={errors.base_salary?.message}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  }}
                  {...register("base_salary")}
                />
              </Box>
              <Box>
                <TextField
                  label="Bonus"
                  fullWidth
                  error={Boolean(errors.bonus_cents)}
                  helperText={errors.bonus_cents?.message}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  }}
                  {...register("bonus_cents")}
                />
              </Box>
              <Box>
                <TextField
                  label="Allowances"
                  fullWidth
                  error={Boolean(errors.allowances_cents)}
                  helperText={errors.allowances_cents?.message}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  }}
                  {...register("allowances_cents")}
                />
              </Box>
            </Box>
            {isEdit && editState.payChanged ? (
              <Box sx={{ mt: 2.5, maxWidth: 480 }}>
                <TextField
                  label="Reason for change"
                  fullWidth
                  helperText="Optional. Defaults to Manual edit."
                  {...register("change_reason")}
                />
                <FieldError message={errors.change_reason?.message} />
              </Box>
            ) : null}

            <Typography color="text.secondary" sx={{ mt: 2 }}>
              {`Total: ${formatUsd(totalCents)}${
                localTotalCents !== null && selectedCountry
                  ? ` (approximate: ${formatLocal(
                      localTotalCents,
                      selectedCountry.currency_code,
                    )} ${selectedCountry.currency_code})`
                  : ""
              }`}
            </Typography>

            <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2, mt: 4 }}>
              <Button variant="outlined" onClick={() => requestLeave(cancelPath)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={isSubmitting || (isEdit && !hasChanges)}
              >
                {isSubmitting ? "Saving…" : "Save employee"}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <Dialog open={discardOpen} onClose={() => setDiscardOpen(false)}>
        <DialogTitle>Discard changes?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            You have unsaved changes. Discard them and leave this page?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDiscardOpen(false)}>Keep editing</Button>
          <Button color="error" onClick={discardChanges}>
            Discard
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
