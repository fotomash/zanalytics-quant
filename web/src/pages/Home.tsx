import { Grid, Typography } from '@mui/material'
import MetricCard from '../components/MetricCard'
import Donut from '../components/Donut'

export default function Home() {
  // Mock values for now; wire to API later
  const vitals = {
    discipline_score: 87,
    patience_index: 142,
    conviction_rate: 73,
    profit_efficiency: 68,
    current_pnl: 2847
  }

  return (
    <>
      <Typography variant="h4" fontWeight={800}>Pulse Command Center</Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Your trading cockpit - where clarity meets conviction
      </Typography>

      <Grid container spacing={2} mt={1}>
        <Grid item xs={12} md={3}>
          <MetricCard title="Discipline Score" value={vitals.discipline_score} unit="%" color="#34D399" trend="up" description="Adherence to predefined rules today" />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard title="Patience Index" value={vitals.patience_index} unit="sec" color="#60A5FA" trend="stable" description="Average time between trades" />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard title="Conviction Rate" value={vitals.conviction_rate} unit="%" color="#A78BFA" trend="up" description="Win rate of high-confidence setups" />
        </Grid>
        <Grid item xs={12} md={3}>
          <MetricCard title="Profit Efficiency" value={vitals.profit_efficiency} unit="%" color="#FBBF24" trend="down" description="Profit captured vs. peak potential" />
        </Grid>
      </Grid>

      <Grid container spacing={2} mt={0.5}>
        <Grid item xs={12} md={4}>
          <Donut title="Equity vs SoD" value={65} subtitle="pnl today" gradient={["#12C48B", "#0AA66E"]} />
        </Grid>
        <Grid item xs={12} md={4}>
          <Donut title="Position Exposure" value={30} subtitle="of daily risk budget" gradient={["#F59E0B", "#D97706"]} />
        </Grid>
        <Grid item xs={12} md={4}>
          <Donut title="Behavioral Posture" value={73} subtitle="composite" gradient={["#10B981", "#059669"]} />
        </Grid>
      </Grid>
    </>
  )
}

