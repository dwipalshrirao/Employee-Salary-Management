import { z } from "zod";

import { parseDollarsToCents } from "./money";

export const MAX_AMOUNT_CENTS = 1_000_000_000;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function amountCents(value) {
  try {
    return parseDollarsToCents(value);
  } catch {
    return null;
  }
}

const baseSalary = z.string().superRefine((value, context) => {
  if (!value.trim()) {
    context.addIssue({ code: "custom", message: "Base salary is required" });
    return;
  }
  const cents = amountCents(value);
  if (cents === null) {
    context.addIssue({ code: "custom", message: "Enter a valid dollar amount" });
  } else if (cents <= 0) {
    context.addIssue({ code: "custom", message: "Base salary must be greater than $0" });
  } else if (cents > MAX_AMOUNT_CENTS) {
    context.addIssue({ code: "custom", message: "Base salary is too large" });
  }
});

function optionalAmount(label) {
  return z.string().superRefine((value, context) => {
    if (!value.trim()) {
      return;
    }
    const cents = amountCents(value);
    if (cents === null) {
      context.addIssue({ code: "custom", message: `Enter a valid ${label.toLowerCase()}` });
    } else if (cents > MAX_AMOUNT_CENTS) {
      context.addIssue({ code: "custom", message: `${label} is too large` });
    }
  });
}

const hireDate = z.string().superRefine((value, context) => {
  if (!value) {
    context.addIssue({ code: "custom", message: "Hire date is required" });
  } else if (value > today()) {
    context.addIssue({ code: "custom", message: "Hire date cannot be in the future" });
  }
});

export const employeeFormSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Full name is required")
    .max(120, "Full name must be 120 characters or fewer"),
  email: z
    .string()
    .trim()
    .min(1, "Enter a valid email")
    .email("Enter a valid email")
    .max(254, "Email must be 254 characters or fewer"),
  department_id: z.string().min(1, "Select a department"),
  job_title_id: z.string().min(1, "Select a job title"),
  country_code: z.string().min(1, "Select a country"),
  manager_id: z.string().optional(),
  hire_date: hireDate,
  base_salary: baseSalary,
  bonus_cents: optionalAmount("Bonus"),
  allowances_cents: optionalAmount("Allowances"),
  change_reason: z.string().max(200, "Reason must be 200 characters or fewer").optional(),
});

export const bulkUpdateFormSchema = z
  .object({
    country_code: z.string().optional(),
    department_id: z.string().optional(),
    job_title_id: z.string().optional(),
    manager_id: z.string().optional(),
    component: z.enum(["base", "bonus", "allowances"]),
    mode: z.enum(["percent", "fixed_amount"]),
    value: z.string(),
    reason: z
      .string()
      .trim()
      .min(1, "Reason is required")
      .max(200, "Reason must be 200 characters or fewer"),
    apply_to_all: z.boolean(),
  })
  .superRefine((values, context) => {
    const hasFilter = ["country_code", "department_id", "job_title_id", "manager_id"].some(
      (field) => values[field],
    );
    if (!hasFilter && !values.apply_to_all) {
      context.addIssue({
        code: "custom",
        path: ["apply_to_all"],
        message: "Choose a filter or apply to all active employees",
      });
    }

    const value = values.value.trim();
    if (!value) {
      context.addIssue({
        code: "custom",
        path: ["value"],
        message: "Adjustment value is required",
      });
      return;
    }

    if (values.mode === "percent") {
      if (!/^[+-]?\d+(\.\d{1,2})?$/.test(value)) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Enter a percentage with at most two decimals",
        });
        return;
      }
      const percentage = Number(value);
      if (percentage === 0) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Percentage cannot be zero",
        });
      } else if (percentage < -50 || percentage > 100) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Percentage must be between -50 and 100",
        });
      }
    } else {
      const cents = amountCents(value);
      if (cents === null) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Enter a valid dollar amount",
        });
      } else if (cents <= 0) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Amount must be greater than $0",
        });
      } else if (cents > MAX_AMOUNT_CENTS) {
        context.addIssue({
          code: "custom",
          path: ["value"],
          message: "Amount is too large",
        });
      }
    }
  });
