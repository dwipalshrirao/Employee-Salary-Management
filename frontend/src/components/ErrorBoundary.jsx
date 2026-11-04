import { Component } from "react";
import { Box, Button, Typography } from "@mui/material";

import { logUnexpectedError } from "../lib/logger";

export default class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    logUnexpectedError("react-error-boundary", error, {
      componentStack: errorInfo.componentStack,
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          role="alert"
          sx={{
            minHeight: "100vh",
            display: "grid",
            placeItems: "center",
            bgcolor: "background.default",
            px: 3,
          }}
        >
          <Box sx={{ maxWidth: 480, textAlign: "center" }}>
            <Typography variant="h1" component="h1">
              Something went wrong
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
              The page could not be displayed. Reload to try again.
            </Typography>
            <Button variant="contained" onClick={() => window.location.reload()}>
              Reload application
            </Button>
          </Box>
        </Box>
      );
    }

    return this.props.children;
  }
}
