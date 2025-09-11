import { Typography, Card, CardContent } from '@mui/material'

export default function Whisperer() {
  return (
    <>
      <Typography variant="h4" fontWeight={800}>The Whisperer Interface</Typography>
      <Typography variant="subtitle1" color="text.secondary" gutterBottom>
        Your AI trading companion - always listening, always learning
      </Typography>
      <Card variant="outlined"><CardContent>
        <Typography>Chat timeline and suggestions (placeholder)</Typography>
      </CardContent></Card>
    </>
  )
}

