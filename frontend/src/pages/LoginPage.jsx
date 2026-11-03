import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  IconButton,
  InputAdornment,
  TextField,
  Typography,
} from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";

function messageFor(error) {
  if (error instanceof ApiError && error.status === 401) {
    return "Invalid email or password";
  }
  if (error instanceof ApiError && error.status === 429) {
    return "Too many attempts. Try again in a few minutes.";
  }
  return "Unable to sign in. Please try again.";
}

function requestedPath(state) {
  const from = state?.from;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}

export default function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const didJustLogin = useRef(false);
  const emailInput = useRef(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const redirectTo = requestedPath(location.state);

  useEffect(() => {
    if (status === "authenticated") {
      navigate(didJustLogin.current ? redirectTo : "/", { replace: true });
    }
  }, [navigate, redirectTo, status]);

  useEffect(() => {
    if (status === "anonymous") {
      emailInput.current?.focus();
    }
  }, [status]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (submitting) {
      return;
    }

    setError("");
    setSubmitting(true);
    didJustLogin.current = true;
    try {
      await login({ email, password });
    } catch (caught) {
      didJustLogin.current = false;
      setError(messageFor(caught));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading") {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          bgcolor: "background.default",
        }}
      >
        <CircularProgress aria-label="Checking session" />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        bgcolor: "background.default",
        px: 3,
        py: 4,
      }}
    >
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography
            variant="caption"
            component="p"
            sx={{
              color: "primary.main",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            ACME Salary Management
          </Typography>
          <Typography variant="h1" component="h1" sx={{ mt: 1.5 }}>
            Sign in
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
            Use your HR account to continue
          </Typography>

          <Box
            component="form"
            noValidate
            onSubmit={handleSubmit}
            sx={{ mt: 3, display: "flex", flexDirection: "column", gap: 2 }}
          >
            <Box>
              <Typography
                component="label"
                htmlFor="login-email"
                variant="caption"
                sx={{ display: "block", mb: 1, color: "text.primary", fontWeight: 600 }}
              >
                Email
              </Typography>
              <TextField
                id="login-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@acme.corp"
                autoComplete="email"
                inputRef={emailInput}
                required
                fullWidth
                disabled={submitting}
                error={Boolean(error)}
              />
            </Box>

            <Box>
              <Typography
                component="label"
                htmlFor="login-password"
                variant="caption"
                sx={{ display: "block", mb: 1, color: "text.primary", fontWeight: 600 }}
              >
                Password
              </Typography>
              <TextField
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••••••"
                autoComplete="current-password"
                required
                fullWidth
                disabled={submitting}
                error={Boolean(error)}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        type="button"
                        edge="end"
                        size="small"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        onClick={() => setShowPassword((visible) => !visible)}
                        disabled={submitting}
                      >
                        <Typography variant="caption" component="span">
                          {showPassword ? "Hide" : "Show"}
                        </Typography>
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Box>

            <Button
              type="submit"
              variant="contained"
              fullWidth
              disabled={submitting}
              startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : undefined}
              sx={{ mt: 1 }}
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>

            {error ? (
              <Alert severity="error" sx={{ mt: 0 }}>
                {error}
              </Alert>
            ) : null}
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
