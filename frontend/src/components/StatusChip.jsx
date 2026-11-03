import { Chip } from "@mui/material";

export default function StatusChip({ status }) {
  const active = status === "active";

  return (
    <Chip
      size="small"
      label={active ? "Active" : "Inactive"}
      sx={{
        bgcolor: active ? "#E6F4EA" : "#EEF0F4",
        color: active ? "success.main" : "text.secondary",
        fontWeight: 600,
      }}
    />
  );
}
