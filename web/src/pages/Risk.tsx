import { Grid, Typography, Card, CardContent } from '@mui/material'
import Donut from '../components/Donut'

export default function Risk() {
  return (
    <>
      <Typography variant="h4" fontWeight={800}>Risk & Performance Guardian</Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Trade with discipline, sleep with confidence
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}><Donut title="Equity vs SoD" value={55} subtitle="pnl today" /></Grid>
        <Grid item xs={12} md={4}><Donut title="Position Exposure" value={40} subtitle="of daily risk budget" /></Grid>
        <Grid item xs={12} md={4}><Donut title="Behavioral Posture" value={70} subtitle="composite" /></Grid>
      </Grid>

      <Grid container spacing={2} mt={0.5}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined"><CardContent>
            <Typography>Recent trades and drawdown guardrails (placeholder)</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card variant="outlined"><CardContent>
            <Typography>Risk alerts and policy (placeholder)</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>
    </>
  )
}

