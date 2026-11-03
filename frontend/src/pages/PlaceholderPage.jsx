import { Box, Typography } from "@mui/material";

export default function PlaceholderPage({ title }) {
  return (
    <Box>
      <Typography variant="h1" component="h1">
        {title}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        This page will be built in a later slice.
      </Typography>
    </Box>
  );
}
