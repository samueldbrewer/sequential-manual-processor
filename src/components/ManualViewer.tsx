import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Breadcrumbs,
  Link,
  Paper,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from '@mui/material';
import {
  ArrowBack,
  Description,
  Language,
  Download,
  OpenInNew,
  Home,
  Build,
  Factory,
  AutoAwesome,
  PictureAsPdf,
} from '@mui/icons-material';
import { Manual, Manufacturer, Model } from '../types';
import api from '../services/api';

interface ManualViewerProps {
  manuals: Manual[];
  manufacturer: Manufacturer;
  model: Model;
  onBack: () => void;
  onReset: () => void;
}

const ManualViewer: React.FC<ManualViewerProps> = ({
  manuals,
  manufacturer,
  model,
  onBack,
  onReset,
}) => {
  const [processDialogOpen, setProcessDialogOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<any>(null);

  const handleOpenManual = (manual: Manual) => {
    window.open(manual.url, '_blank');
  };

  const handleProcessManual = async (manual: Manual) => {
    setProcessDialogOpen(true);
    setProcessing(true);
    setProcessResult(null);

    try {
      const result = await api.processManual(manual.url);
      setProcessResult(result);
    } catch (error) {
      setProcessResult({
        success: false,
        error: 'Failed to process manual. Please try again.',
      });
    } finally {
      setProcessing(false);
    }
  };

  const getManualIcon = (type: string) => {
    if (type.toLowerCase().includes('service')) return '🔧';
    if (type.toLowerCase().includes('parts')) return '🔩';
    if (type.toLowerCase().includes('wiring')) return '⚡';
    if (type.toLowerCase().includes('installation')) return '📦';
    if (type.toLowerCase().includes('operation')) return '📖';
    return '📄';
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Breadcrumbs aria-label="breadcrumb">
          <Link
            component="button"
            underline="hover"
            color="inherit"
            onClick={onReset}
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <Home sx={{ mr: 0.5, fontSize: 20 }} />
            Home
          </Link>
          <Link
            component="button"
            underline="hover"
            color="inherit"
            onClick={onReset}
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <Factory sx={{ mr: 0.5, fontSize: 20 }} />
            {manufacturer.name}
          </Link>
          <Link
            component="button"
            underline="hover"
            color="inherit"
            onClick={onBack}
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <Build sx={{ mr: 0.5, fontSize: 20 }} />
            Models
          </Link>
          <Typography color="text.primary">{model.name}</Typography>
        </Breadcrumbs>
      </Box>

      <Card elevation={0} sx={{ mb: 3, border: '1px solid', borderColor: 'divider' }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
            <Box>
              <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
                {model.name}
              </Typography>
              {model.description && (
                <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
                  {model.description}
                </Typography>
              )}
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip label={manufacturer.name} color="primary" variant="outlined" />
                <Chip
                  icon={<Description sx={{ fontSize: 16 }} />}
                  label={`${manuals.length} manual${manuals.length !== 1 ? 's' : ''} available`}
                  color="success"
                  variant="outlined"
                />
              </Box>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button startIcon={<ArrowBack />} onClick={onBack} variant="outlined">
                Back to Models
              </Button>
              <Button startIcon={<Home />} onClick={onReset} variant="outlined">
                Start Over
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {manuals.length === 0 ? (
        <Alert severity="info">
          No manuals available for this model. Please check back later or contact support.
        </Alert>
      ) : (
        <Box sx={{ display: 'flex', gap: 3, flexDirection: { xs: 'column', md: 'row' } }}>
          <Box sx={{ flex: { xs: 1, md: 2 } }}>
            <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider' }}>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Available Manuals
              </Typography>
              <List>
                {manuals.map((manual, index) => (
                  <React.Fragment key={index}>
                    {index > 0 && <Divider />}
                    <ListItem sx={{ py: 2 }}>
                      <ListItemIcon>
                        <Box sx={{ fontSize: 24 }}>{getManualIcon(manual.type)}</Box>
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Typography variant="subtitle1" sx={{ fontWeight: 500 }}>
                            {manual.type}
                          </Typography>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                              {manual.format && (
                                <Chip
                                  icon={<PictureAsPdf sx={{ fontSize: 16 }} />}
                                  label={manual.format}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                              {manual.language && (
                                <Chip
                                  icon={<Language sx={{ fontSize: 16 }} />}
                                  label={manual.language.toUpperCase()}
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          </Box>
                        }
                      />
                      <ListItemSecondaryAction>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            edge="end"
                            aria-label="open"
                            onClick={() => handleOpenManual(manual)}
                            color="primary"
                          >
                            <OpenInNew />
                          </IconButton>
                          <IconButton
                            edge="end"
                            aria-label="download"
                            onClick={() => window.open(manual.url, '_blank')}
                            color="primary"
                          >
                            <Download />
                          </IconButton>
                        </Box>
                      </ListItemSecondaryAction>
                    </ListItem>
                  </React.Fragment>
                ))}
              </List>
            </Paper>
          </Box>

          <Box sx={{ flex: 1 }}>
            <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider' }}>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                AI Processing
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Use AI to extract step-by-step procedures, visuals, and create enhanced smart manuals
              </Typography>
              <Button
                fullWidth
                variant="contained"
                startIcon={<AutoAwesome />}
                onClick={() => manuals.length > 0 && handleProcessManual(manuals[0])}
                disabled={manuals.length === 0}
                sx={{ mb: 2 }}
              >
                Process with AI
              </Button>
              <Alert severity="info" variant="outlined">
                <Typography variant="body2">
                  The AI processor will:
                </Typography>
                <List dense>
                  <ListItem>• Extract step-by-step workflows</ListItem>
                  <ListItem>• Identify and catalog visuals</ListItem>
                  <ListItem>• Create enhanced documentation</ListItem>
                  <ListItem>• Generate training modules</ListItem>
                </List>
              </Alert>
            </Paper>
          </Box>
        </Box>
      )}

      <Dialog
        open={processDialogOpen}
        onClose={() => setProcessDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>AI Manual Processing</DialogTitle>
        <DialogContent>
          {processing ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3 }}>
              <CircularProgress sx={{ mb: 2 }} />
              <Typography>Processing manual with AI...</Typography>
              <Typography variant="body2" color="text.secondary">
                This may take 2-3 minutes
              </Typography>
            </Box>
          ) : processResult ? (
            <Box>
              {processResult.success ? (
                <Alert severity="success" sx={{ mb: 2 }}>
                  Manual processing initiated successfully!
                </Alert>
              ) : (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {processResult.error}
                </Alert>
              )}
              {processResult.components && (
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Processing Components:
                  </Typography>
                  <List dense>
                    {Object.entries(processResult.components).map(([key, value]) => (
                      <ListItem key={key}>
                        <ListItemText primary={value as string} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setProcessDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ManualViewer;