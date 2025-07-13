import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Avatar,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import { Box as MuiBox } from '@mui/material';
import Chip from '@mui/material/Chip';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Description as DescriptionIcon,
  ListAlt as ListAltIcon,
  Analytics as AnalyticsIcon,
  AccountCircle,
  Logout,
  LockReset as LockResetIcon,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Snackbar from '@mui/material/Snackbar';
import CircularProgress from '@mui/material/CircularProgress';
import InputAdornment from '@mui/material/InputAdornment';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';

const drawerWidth = 240;

const logoBoxStyle = {
  width: '100%',
  height: 100,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  p: 0.5,
  background: 'transparent',
};

const logoImgStyle = {
  width: '100%',
  height: '100%',
  objectFit: 'contain',
  display: 'block',
};

function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const { user, logout } = useAuth();
  const [anchorEl, setAnchorEl] = React.useState(null);
  const [changePwdOpen, setChangePwdOpen] = React.useState(false);
  const [pwdForm, setPwdForm] = React.useState({ current: '', new: '', confirm: '' });
  const [pwdLoading, setPwdLoading] = React.useState(false);
  const [pwdError, setPwdError] = React.useState('');
  const [pwdSnackbar, setPwdSnackbar] = React.useState({ open: false, message: '', severity: 'success' });
  const [showCurrent, setShowCurrent] = React.useState(false);
  const [showNew, setShowNew] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);
  const [version, setVersion] = useState('');

  useEffect(() => {
    fetch('/api/version')
      .then(res => res.json())
      .then(data => {
        let safeVersion = 'dev';
        if (data && typeof data === 'object' && data.version) {
          safeVersion = typeof data.version === 'string' ? data.version : String(data.version);
        } else if (typeof data === 'string') {
          safeVersion = data;
        } else if (data) {
          safeVersion = String(data);
        }
        setVersion(safeVersion);
      })
      .catch(() => setVersion('dev'));
  }, []);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleUserMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    handleUserMenuClose();
    navigate('/login');
  };

  const handleChangePwdOpen = () => {
    setChangePwdOpen(true);
    setPwdForm({ current: '', new: '', confirm: '' });
    setPwdError('');
  };
  const handleChangePwdClose = () => {
    setChangePwdOpen(false);
    setPwdError('');
  };
  const handlePwdInput = (e) => {
    setPwdForm({ ...pwdForm, [e.target.name]: e.target.value });
  };
  const handlePwdSubmit = async (e) => {
    e.preventDefault();
    setPwdLoading(true);
    setPwdError('');
    if (pwdForm.new.length < 8) {
      setPwdError('New password must be at least 8 characters.');
      setPwdLoading(false);
      return;
    }
    if (pwdForm.new !== pwdForm.confirm) {
      setPwdError('Passwords do not match.');
      setPwdLoading(false);
      return;
    }
    try {
      const res = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({ current_password: pwdForm.current, new_password: pwdForm.new })
      });
      const data = await res.json();
      if (data.success) {
        setPwdSnackbar({ open: true, message: 'Password changed successfully! Please log in again.', severity: 'success' });
        setChangePwdOpen(false);
        setTimeout(async () => {
          await logout();
          navigate('/login');
        }, 1200);
      } else {
        setPwdError(data.message || 'Failed to change password.');
      }
    } catch (err) {
      setPwdError('Failed to change password.');
    }
    setPwdLoading(false);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'Reports', icon: <DescriptionIcon />, path: '/reports' },
    { text: 'Logs', icon: <ListAltIcon />, path: '/logs' },
    { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  const drawer = (
    <div>
      <Box sx={logoBoxStyle}>
        <img
          src={process.env.PUBLIC_URL + '/th-owl-logo.png'}
          alt="TH OWL Logo"
          style={logoImgStyle}
        />
      </Box>
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => navigate(item.path)}
            selected={location.pathname === item.path}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', width: '100vw', margin: 0, padding: 0, background: '#000' }}>
      <Box sx={{ display: 'flex' }}>
        <AppBar
          position="fixed"
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              CARLA Simulator
            </Typography>
            
            {user && (
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Typography variant="body2" sx={{ mr: 1 }}>
                  {user.username}
                </Typography>
                <IconButton
                  color="inherit"
                  onClick={handleUserMenuOpen}
                  sx={{ ml: 1 }}
                >
                  <Avatar sx={{ width: 32, height: 32 }}>
                    <AccountCircle />
                  </Avatar>
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleUserMenuClose}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                  }}
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                  }}
                >
                  <MenuItem disabled>
                    <Typography variant="body2">
                      {user.first_name} {user.last_name}
                    </Typography>
                  </MenuItem>
                  <MenuItem disabled>
                    <Typography variant="caption" color="text.secondary">
                      {user.email}
                    </Typography>
                  </MenuItem>
                  <Divider />
                  <MenuItem onClick={handleChangePwdOpen}>
                    <ListItemIcon>
                      <LockResetIcon fontSize="small" />
                    </ListItemIcon>
                    Change Password
                  </MenuItem>
                  <MenuItem onClick={handleLogout}>
                    <ListItemIcon>
                      <Logout fontSize="small" />
                    </ListItemIcon>
                    Logout
                  </MenuItem>
                </Menu>
              </Box>
            )}
          </Toolbar>
        </AppBar>
        <Box
          component="nav"
          sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        >
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true,
            }}
            sx={{
              display: { xs: 'block', sm: 'none' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
              },
            }}
          >
            {drawer}
          </Drawer>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: 'none', sm: 'block' },
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
              },
            }}
            open
          >
            {drawer}
          </Drawer>
        </Box>
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 1.5,
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            boxSizing: 'border-box',
          }}
        >
          <Toolbar />
          {children}
        </Box>
      </Box>

      <Box
        sx={{
          position: 'fixed',
          bottom: 8,
          left: 16,
          zIndex: 1300,
          color: 'rgba(255,255,255,0.5)',
          fontSize: 13,
          fontFamily: 'Roboto, sans-serif',
          letterSpacing: 1,
          userSelect: 'none',
        }}
      >
        {typeof version === 'string' ? version : String(version)}
      </Box>
      <Dialog open={changePwdOpen} onClose={handleChangePwdClose} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ pb: 0, pt: 2}}>Change Password</DialogTitle>
        <form onSubmit={handlePwdSubmit} autoComplete="off">
          <DialogContent sx={{ pt: 1, px: 5, pb: 5, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <TextField
              label="Current Password"
              name="current"
              type={showCurrent ? 'text' : 'password'}
              value={pwdForm.current}
              onChange={handlePwdInput}
              fullWidth
              required
              margin="normal"
              size="small"
              autoComplete="current-password"
              sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle current password visibility"
                      onClick={() => setShowCurrent((show) => !show)}
                      edge="end"
                      size="small"
                    >
                      {showCurrent ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="New Password"
              name="new"
              type={showNew ? 'text' : 'password'}
              value={pwdForm.new}
              onChange={handlePwdInput}
              fullWidth
              required
              margin="normal"
              size="small"
              autoComplete="new-password"
              sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle new password visibility"
                      onClick={() => setShowNew((show) => !show)}
                      edge="end"
                      size="small"
                    >
                      {showNew ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            <TextField
              label="Confirm New Password"
              name="confirm"
              type={showConfirm ? 'text' : 'password'}
              value={pwdForm.confirm}
              onChange={handlePwdInput}
              fullWidth
              required
              margin="normal"
              size="small"
              autoComplete="new-password"
              sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle confirm password visibility"
                      onClick={() => setShowConfirm((show) => !show)}
                      edge="end"
                      size="small"
                    >
                      {showConfirm ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />
            {pwdError && <Typography color="error" variant="body2" sx={{ mt: 1 }}>{pwdError}</Typography>}
          </DialogContent>
          <DialogActions sx={{ pb: 3, pl: 3, pr: 5, pt: 0 }}>
            <Button onClick={handleChangePwdClose} color="secondary" size="small" sx={{ borderRadius: 2, color: '#D32F2F'}}>Cancel</Button>
            <Button type="submit" variant="contained" color="primary" size="small" disabled={pwdLoading} sx={{ borderRadius: 2}}>
              {pwdLoading ? <CircularProgress size={18} color="inherit" /> : 'Change Password'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <Snackbar
        open={pwdSnackbar.open}
        autoHideDuration={4000}
        onClose={() => setPwdSnackbar({ ...pwdSnackbar, open: false })}
        message={pwdSnackbar.message}
      />
    </div>
  );
}

function VersionLabel() {
  return (
    <MuiBox
      sx={{
        position: 'fixed',
        left: 12,
        bottom: 12,
        zIndex: 2000,
        background: 'none',
        boxShadow: 'none',
        p: 0,
      }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500, fontSize: 14, letterSpacing: 1 }}>
        Version: dev_v1.4.2
      </Typography>
    </MuiBox>
  );
}

export default function LayoutWithVersion(props) {
  return (
    <>
      <Layout {...props} />
      <VersionLabel />
    </>
  );
} 