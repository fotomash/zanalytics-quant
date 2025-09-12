import { Typography, Grid, Card, CardContent } from '@mui/material'

export default function Intelligence() {
  return (
    <>
      <Typography variant="h4" fontWeight={800}>Market Intelligence Hub</Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        See what others miss - market structure decoded
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card variant="outlined"><CardContent>
            <Typography>Confluence heatmap (placeholder)</Typography>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card variant="outlined"><CardContent>
            <Typography>Bias and regime detection (placeholder)</Typography>
          </CardContent></Card>
        </Grid>
      </Grid>
    </>
  )
}

