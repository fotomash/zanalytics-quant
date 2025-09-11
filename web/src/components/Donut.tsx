import { Pie, PieChart, ResponsiveContainer, Cell } from 'recharts'
import { Card, CardContent, Stack, Typography } from '@mui/material'

export default function Donut({ title, value, max = 100, subtitle, gradient = ['#10B981', '#374151'] }: {
  title: string
  value: number
  max?: number
  subtitle?: string
  gradient?: [string, string] | string[]
}) {
  const frac = Math.max(0, Math.min(1, value / max))
  const data = [
    { name: 'used', value: frac },
    { name: 'rest', value: 1 - frac }
  ]
  const colors = [gradient[0], '#273244']

  return (
    <Card variant="outlined" sx={{ bgcolor: '#0F172A', borderColor: '#1f2a3c' }}>
      <CardContent>
        <Typography variant="subtitle2" color="text.secondary">{title}</Typography>
        <Stack alignItems="center" justifyContent="center" sx={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie data={data} innerRadius={60} outerRadius={80} startAngle={90} endAngle={-270} dataKey="value">
                {data.map((entry, idx) => (
                  <Cell key={`cell-${idx}`} fill={colors[idx]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </Stack>
        <Stack alignItems="center" mt={-20}>
          <Typography variant="h5" fontWeight={800}>{Math.round(frac * 100)}%</Typography>
          {subtitle && <Typography variant="caption" color="text.secondary">{subtitle}</Typography>}
        </Stack>
      </CardContent>
    </Card>
  )
}

