import { Card, CardContent, Skeleton, Typography } from "@mui/material";

export default function StatCard({ title, value, subtitle, loading = false }) {
  return (
    <Card>
      <CardContent sx={{ p: 2.5 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", fontWeight: 600, textTransform: "uppercase" }}
        >
          {title}
        </Typography>
        {loading ? (
          <Skeleton width="70%" height={44} />
        ) : (
          <Typography variant="h1" sx={{ mt: 0.5, fontSize: "1.6rem", lineHeight: 1.4 }}>
            {value}
          </Typography>
        )}
        {loading ? (
          <Skeleton width="45%" height={20} />
        ) : subtitle ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {subtitle}
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
}
