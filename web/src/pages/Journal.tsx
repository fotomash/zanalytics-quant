import { Typography, Card, CardContent } from '@mui/material'

export default function Journal() {
  return (
    <>
      <Typography variant="h4" fontWeight={800}>Decision Journal & Analytics</Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Learn from every decision - your path to consistent profitability
      </Typography>
      <Card variant="outlined"><CardContent>
        <Typography>Journal entries, tags, and analytics (placeholder)</Typography>
      </CardContent></Card>
    </>
  )
}

