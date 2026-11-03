import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { AppBar, Avatar, Box, Button, Menu, MenuItem, Toolbar, Typography } from "@mui/material";

const navItems = [
  { label: "Dashboard", to: "/", end: true },
  { label: "Employees", to: "/employees" },
  { label: "History", to: "/history" },
  { label: "Bulk update", to: "/bulk-update" },
];

export default function AppShell() {
  const [menuAnchor, setMenuAnchor] = useState(null);
  const menuOpen = Boolean(menuAnchor);

  const openMenu = (event) => setMenuAnchor(event.currentTarget);
  const closeMenu = () => setMenuAnchor(null);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="sticky">
        <Toolbar sx={{ maxWidth: 1280, width: "100%", mx: "auto", px: 3, gap: 4 }}>
          <Button
            component={NavLink}
            to="/"
            color="inherit"
            sx={{
              px: 0,
              color: "text.primary",
              fontSize: "1rem",
              "&:hover": { bgcolor: "transparent" },
            }}
          >
            ACME Salary Management
          </Button>

          <Box component="nav" sx={{ display: "flex", gap: 3, flex: 1 }}>
            {navItems.map((item) => (
              <Button
                key={item.to}
                component={NavLink}
                to={item.to}
                end={item.end}
                sx={{
                  height: 64,
                  px: 0,
                  borderRadius: 0,
                  color: "text.secondary",
                  fontWeight: 400,
                  borderBottom: "2px solid transparent",
                  "&:hover": { bgcolor: "transparent", color: "text.primary" },
                  "&.active": {
                    color: "primary.main",
                    fontWeight: 600,
                    borderBottomColor: "primary.main",
                  },
                }}
              >
                {item.label}
              </Button>
            ))}
          </Box>

          <Button
            aria-label="Account menu"
            aria-controls={menuOpen ? "account-menu" : undefined}
            aria-haspopup="true"
            aria-expanded={menuOpen ? "true" : undefined}
            onClick={openMenu}
            sx={{ gap: 1, color: "text.primary", px: 1 }}
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: 14 }}>
              SJ
            </Avatar>
            <Box sx={{ textAlign: "left", display: { xs: "none", sm: "block" } }}>
              <Typography sx={{ fontSize: 14, fontWeight: 600, lineHeight: 1.2 }}>
                Sarah Jenkins
              </Typography>
              <Typography sx={{ fontSize: 12, color: "text.secondary", lineHeight: 1.2 }}>
                HR Manager
              </Typography>
            </Box>
          </Button>

          <Menu
            id="account-menu"
            anchorEl={menuAnchor}
            open={menuOpen}
            onClose={closeMenu}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <MenuItem onClick={closeMenu} sx={{ color: "error.main" }}>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box component="main" sx={{ maxWidth: 1280, mx: "auto", px: 3, py: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
