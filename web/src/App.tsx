import { Route, Routes, Navigate } from 'react-router-dom'
import { createTheme, CssBaseline, ThemeProvider } from '@mui/material'
import Layout from './components/Layout'
import Home from './pages/Home'
import Intelligence from './pages/Intelligence'
import Risk from './pages/Risk'
import Whisperer from './pages/Whisperer'
import Journal from './pages/Journal'

const dark = createTheme({
  palette: {
    mode: 'dark',
    background: { default: '#111827', paper: '#1F2937' },
    text: { primary: '#D1D5DB', secondary: '#9CA3AF' },
    primary: { main: '#34D399' },
    secondary: { main: '#60A5FA' }
  },
  shape: { borderRadius: 10 }
})

export default function App() {
  return (
    <ThemeProvider theme={dark}>
      <CssBaseline />
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="/home" element={<Home />} />
          <Route path="/intelligence" element={<Intelligence />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/whisperer" element={<Whisperer />} />
          <Route path="/journal" element={<Journal />} />
        </Routes>
      </Layout>
    </ThemeProvider>
  )
}

