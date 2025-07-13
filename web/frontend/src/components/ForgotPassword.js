import React, { useState } from 'react';
import { Card, CardContent, Typography, Box, TextField, Button, Snackbar, IconButton, InputAdornment } from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Link from '@mui/material/Link';
import GitHubIcon from '@mui/icons-material/GitHub';

const ForgotPassword = () => {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('');
  const [userExists, setUserExists] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const navigate = useNavigate();

  const handleUsernameSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await axios.post('/api/auth/check-username', { username });
      if (res.data.exists) {
        setUserExists(true);
        setStep(2);
      } else {
        setError('User not found');
      }
    } catch (err) {
      setError('User not found');
    }
    setLoading(false);
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      setLoading(false);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      setLoading(false);
      return;
    }
    try {
      await axios.post('/api/auth/reset-password', { username, new_password: newPassword });
      setSnackbar({ open: true, message: 'Password reset successful! Redirecting to login...', severity: 'success' });
      setTimeout(() => navigate('/login'), 1500);
      setStep(1);
      setUsername('');
      setUserExists(false);
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError('Failed to reset password.');
    }
    setLoading(false);
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', background: 'transparent' }}>
      <Card
        sx={{
          maxWidth: 400,
          width: '100%',
          borderRadius: 3,
          boxShadow: '0 4px 24px rgba(0,0,0,0.10)',
          background: 'rgba(255, 255, 255, 0.08)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          padding: 5,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Box sx={{ width: '100%', display: 'flex', justifyContent: 'center', mb: 2 }}>
          <img
            src={process.env.PUBLIC_URL + '/th-owl-logo.png'}
            alt="TH OWL Logo"
            style={{
              maxHeight: 64,
              width: 'auto',
              objectFit: 'contain',
              display: 'block',
            }}
          />
        </Box>
        <CardContent>
          <Typography variant="h5" component="div" gutterBottom>
            Forgot Password
          </Typography>
          {step === 1 && (
            <form onSubmit={handleUsernameSubmit}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Enter your username to reset your password.
              </Typography>
              <TextField
                label="Username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                fullWidth
                required
                size="small"
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                autoComplete="username"
              />
              {error && <Typography color="error" variant="body2" sx={{ mb: 1 }}>{error}</Typography>}
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Button
                  color="secondary"
                  fullWidth
                  size="small"
                  onClick={() => navigate('/login')}
                  sx={{ borderRadius: 2, color: '#D32F2F' }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={loading || !username}
                  size="small"
                  sx={{ borderRadius: 2 }}
                >
                  {loading ? 'Checking...' : 'Next'}
                </Button>
              </Box>
            </form>
          )}
          {step === 2 && (
            <form onSubmit={handlePasswordSubmit}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Set a new password for <b>{username}</b>.
              </Typography>
              <TextField
                label="New Password"
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                fullWidth
                required
                size="small"
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                autoComplete="new-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle password visibility"
                        onClick={() => setShowPassword((show) => !show)}
                        edge="end"
                        size="small"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <TextField
                label="Confirm Password"
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                fullWidth
                required
                size="small"
                sx={{ mb: 2, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                autoComplete="new-password"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="toggle confirm password visibility"
                        onClick={() => setShowConfirmPassword((show) => !show)}
                        edge="end"
                        size="small"
                      >
                        {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              {error && <Typography color="error" variant="body2" sx={{ mb: 1 }}>{error}</Typography>}
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Button
                  color="secondary"
                  fullWidth
                  size="small"
                  onClick={() => navigate('/login')}
                  sx={{ borderRadius: 2, color: '#D32F2F' }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  color="primary"
                  fullWidth
                  disabled={loading || !newPassword || !confirmPassword}
                  size="small"
                  sx={{ borderRadius: 2 }}
                >
                  {loading ? 'Resetting...' : 'Reset Password'}
                </Button>
              </Box>
            </form>
          )}
        </CardContent>
      </Card>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  );
};

export default ForgotPassword; 