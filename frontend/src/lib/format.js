const DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function formatDate(value) {
  if (!value) {
    return "";
  }
  return DATE_FORMATTER.format(new Date(`${value}T00:00:00Z`));
}

export function initialsFor(name) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  return initials || "HR";
}
