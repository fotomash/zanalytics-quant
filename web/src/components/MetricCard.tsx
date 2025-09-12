import { Card, CardContent, Stack, Typography, Chip } from '@mui/material'

type Trend = 'up' | 'down' | 'stable'

export default function MetricCard({
  title,
  value,
  unit,
  color = '#34D399',
  trend = 'stable',
  description
}: {
  title: string
  value: string | number
  unit?: string
  color?: string
  trend?: Trend
  description?: string
}) {
  const chip = trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'
  const chipColor = trend === 'up' ? 'success' : trend === 'down' ? 'error' : 'default'
  return (
    <Card variant="outlined" sx={{ bgcolor: '#1F2937', borderColor: '#374151', height: '100%' }}>
      <CardContent>
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" mb={1.5}>
          <Typography variant="body2" color="text.secondary" fontWeight={600}>{title}</Typography>
          <Chip size="small" label={chip} color={chipColor as any} sx={{ borderRadius: 1 }} />
        </Stack>
        <Stack direction="row" alignItems="baseline" spacing={1}>
          <Typography variant="h4" fontWeight={800} sx={{ color }}>{value}</Typography>
          {unit && <Typography variant="body2" color="text.secondary">{unit}</Typography>}
        </Stack>
        {description && (
          <Typography variant="caption" color="text.secondary" display="block" mt={1}>{description}</Typography>
        )}
      </CardContent>
    </Card>
  )
}

