import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

const Imprint = () => (
  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh', background: 'transparent' }}>
    <Card sx={{ maxWidth: 480, width: '100%', borderRadius: 3, boxShadow: '0 4px 24px rgba(0,0,0,0.10)', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', p: 5 }}>
      <CardContent>
        <Typography variant="h5" component="div" gutterBottom>
          Imprint
        </Typography>
        <Typography variant="body1" gutterBottom>
          Technische Hochschule Ostwestfalen-Lippe<br/>
          University of Applied Sciences and Arts<br/>
          Campusallee 12, 32657 Lemgo, Germany<br/>
          <br/>
          Contact: info@th-owl.de<br/>
          Phone: +49 5261 702 0
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This application is for academic and research purposes only.<br/>
          &copy; {new Date().getFullYear()} TH OWL
        </Typography>
      </CardContent>
    </Card>
  </Box>
);

export default Imprint; 
