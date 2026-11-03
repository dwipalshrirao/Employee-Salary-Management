const usdFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function formatUsd(cents) {
  const hasCents = cents % 100 !== 0;
  const formatter = hasCents
    ? usdFormatter
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      });

  return formatter.format(cents / 100);
}

export function formatUsdCompact(cents) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(cents / 100);
}

export function formatLocal(cents, currencyCode) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currencyCode,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

export function parseDollarsToCents(input) {
  if (typeof input !== "string") {
    throw new Error("Dollar amount must be a string");
  }

  let cleaned = input.trim();
  if (cleaned.startsWith("$")) {
    cleaned = cleaned.slice(1);
  }
  cleaned = cleaned.replace(/,/g, "");

  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) {
    throw new Error("Enter a valid dollar amount with at most two decimals");
  }

  const [whole, fraction = ""] = cleaned.split(".");
  const cents = Number(`${whole}${fraction.padEnd(2, "0")}`);

  if (!Number.isSafeInteger(cents)) {
    throw new Error("Dollar amount is too large");
  }

  return cents;
}

export function centsToDollarsString(cents) {
  if (!Number.isInteger(cents)) {
    throw new Error("Cents must be an integer");
  }

  const sign = cents < 0 ? "-" : "";
  const absolute = Math.abs(cents);

  return `${sign}${Math.floor(absolute / 100)}.${String(absolute % 100).padStart(2, "0")}`;
}
