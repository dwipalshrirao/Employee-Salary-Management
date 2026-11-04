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
