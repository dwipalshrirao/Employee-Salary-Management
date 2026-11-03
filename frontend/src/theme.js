import { createTheme } from "@mui/material/styles";

const colors = {
  primary: "#1E4ED8",
  primaryDark: "#173DAE",
  primaryTint: "#E8EEFC",
  secondary: "#0F766E",
  success: "#2E7D32",
  warning: "#B45309",
  error: "#C62828",
  background: "#F6F7F9",
  surface: "#FFFFFF",
  tableHeader: "#F1F4F9",
  border: "#E3E7EE",
  textPrimary: "#1A2230",
  textSecondary: "#5B6676",
  textDisabled: "#9AA3B2",
};

const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: colors.primary,
      dark: colors.primaryDark,
      light: colors.primaryTint,
      contrastText: "#FFFFFF",
    },
    secondary: { main: colors.secondary },
    success: { main: colors.success },
    warning: { main: colors.warning },
    error: { main: colors.error },
    background: { default: colors.background, paper: colors.surface },
    text: {
      primary: colors.textPrimary,
      secondary: colors.textSecondary,
      disabled: colors.textDisabled,
    },
    divider: colors.border,
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontSize: "1.75rem", lineHeight: "2.25rem", fontWeight: 600 },
    h2: { fontSize: "1.25rem", lineHeight: "1.75rem", fontWeight: 600 },
    h3: { fontSize: "1rem", lineHeight: "1.5rem", fontWeight: 600 },
    body1: { fontSize: "0.875rem", lineHeight: "1.25rem", fontWeight: 400 },
    body2: { fontSize: "0.875rem", lineHeight: "1.25rem", fontWeight: 400 },
    caption: { fontSize: "0.75rem", lineHeight: "1rem", fontWeight: 400 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 8 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: colors.background },
      },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0, color: "inherit" },
      styleOverrides: {
        root: {
          backgroundColor: colors.surface,
          borderBottom: `1px solid ${colors.border}`,
          boxShadow: "none",
        },
      },
    },
    MuiToolbar: {
      styleOverrides: {
        root: {
          minHeight: 64,
          "@media (min-width:600px)": { minHeight: 64 },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 6, minHeight: 40, paddingInline: 16 },
        sizeSmall: { minHeight: 32 },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${colors.border}`,
          borderRadius: 8,
          boxShadow: "none",
        },
      },
    },
    MuiPaper: {
      styleOverrides: { root: { backgroundImage: "none" } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: colors.tableHeader,
          color: colors.textPrimary,
          fontWeight: 600,
        },
        root: { borderColor: colors.border, padding: 12 },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 8, backgroundColor: colors.surface },
      },
    },
    MuiChip: {
      styleOverrides: { root: { borderRadius: 6 } },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: 8, boxShadow: "0 8px 24px rgba(26, 34, 48, 0.12)" },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: { boxShadow: "0 8px 24px rgba(26, 34, 48, 0.12)" },
      },
    },
    MuiLink: {
      defaultProps: { underline: "hover" },
    },
    MuiTextField: {
      defaultProps: { size: "small" },
    },
  },
});

export default theme;
