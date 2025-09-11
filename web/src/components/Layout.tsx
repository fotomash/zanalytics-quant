import { PropsWithChildren } from 'react'
import { AppBar, Box, Container, Drawer, IconButton, List, ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography } from '@mui/material'
import { useLocation, useNavigate } from 'react-router-dom'
import DashboardIcon from '@mui/icons-material/Dashboard'
import PsychologyIcon from '@mui/icons-material/Psychology'
import SecurityIcon from '@mui/icons-material/Security'
import ChatIcon from '@mui/icons-material/Chat'
import MenuIcon from '@mui/icons-material/Menu'
import BookIcon from '@mui/icons-material/Book'
import { useState } from 'react'

const NAV = [
  { path: '/home', label: 'Pulse Command Center', icon: <DashboardIcon /> },
  { path: '/intelligence', label: 'Market Intelligence Hub', icon: <PsychologyIcon /> },
  { path: '/risk', label: 'Risk & Performance Guardian', icon: <SecurityIcon /> },
  { path: '/whisperer', label: 'The Whisperer Interface', icon: <ChatIcon /> },
  { path: '/journal', label: 'Decision Journal & Analytics', icon: <BookIcon /> }
]

export default function Layout({ children }: PropsWithChildren) {
  const nav = useNavigate()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(true)
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1, bgcolor: '#0B1220' }}>
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={() => setOpen(!open)}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ ml: 1, fontWeight: 800 }}>Zan.Pulse ⚡</Typography>
        </Toolbar>
      </AppBar>
      <Drawer variant="permanent" open={open} sx={{
        width: open ? 260 : 72,
        flexShrink: 0,
        '& .MuiDrawer-paper': { width: open ? 260 : 72, boxSizing: 'border-box', borderRight: '1px solid #374151', bgcolor: '#0F172A' }
      }}>
        <Toolbar />
        <List>
          {NAV.map(item => (
            <ListItemButton key={item.path} selected={pathname === item.path} onClick={() => nav(item.path)}>
              <ListItemIcon sx={{ color: 'text.secondary' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Toolbar />
        <Container maxWidth={false} sx={{ py: 3 }}>{children}</Container>
      </Box>
    </Box>
  )
}

