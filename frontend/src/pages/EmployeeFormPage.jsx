import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  InputAdornment,
  MenuItem,
  TextField,
  Typography,
} from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { createEmployee } from "../api/employees";
import EmployeeAutocomplete from "../components/EmployeeAutocomplete";
import { useLookups } from "../hooks/useLookups";
import { employeeFormSchema } from "../lib/schemas";
import { formatLocal, formatUsd, parseDollarsToCents } from "../lib/money";

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
};

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
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const lookups = useLookups();
  const [serverError, setServerError] = useState("");
  const {
    control,
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(employeeFormSchema),
    defaultValues: DEFAULT_VALUES,
  });

  const watched = watch();
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
  }

  return (
    <Box sx={{ maxWidth: 960, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <RouterLink to="/employees" style={{ color: "inherit", textDecoration: "none" }}>
          Employees
        </RouterLink>
        <Typography color="text.disabled">/</Typography>
        <Typography sx={{ fontWeight: 600 }}>New employee</Typography>
      </Box>
      <Typography variant="h1" component="h1" sx={{ mt: 1, mb: 3 }}>
        Add employee
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
              <Button component={RouterLink} to="/employees" variant="outlined">
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={isSubmitting}>
                {isSubmitting ? "Saving…" : "Save employee"}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
