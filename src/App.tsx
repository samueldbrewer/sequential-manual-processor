import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Typography,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Card,
  CardContent,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Paper,
  Skeleton,
  SelectChangeEvent,
  LinearProgress,
  Divider,
  IconButton,
} from '@mui/material';
import {
  OpenInNew,
  PictureAsPdf,
  Refresh,
  ArrowBack,
  ChevronRight,
  Description as DescriptionIcon,
} from '@mui/icons-material';
import { Manufacturer, Model, Manual } from './types';
import api from './services/api';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#D32F2F', // Matching logo background red
      dark: '#B71C1C',
      light: '#EF5350',
    },
    secondary: {
      main: '#666666',
      dark: '#333333',
      light: '#999999',
    },
    background: {
      default: '#FFFFFF',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontSize: '1.5rem',
      '@media (min-width:600px)': {
        fontSize: '2rem',
      },
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiSelect: {
      styleOverrides: {
        root: {
          minHeight: '48px',
        },
      },
    },
  },
});

function App() {
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [manuals, setManuals] = useState<Manual[]>([]);
  const [selectedManufacturer, setSelectedManufacturer] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [selectedManual, setSelectedManual] = useState<Manual | null>(null);
  const [currentPage, setCurrentPage] = useState<'list' | 'detail'>('list');
  const [manualMetadata, setManualMetadata] = useState<{ pageCount?: number; fileSize?: string; preview?: string; localUrl?: string } | null>(null);
  const [loadingMetadata, setLoadingMetadata] = useState(false);
  const [loadingManufacturers, setLoadingManufacturers] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [loadingManuals, setLoadingManuals] = useState(false);
  const activeModelRequest = useRef<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manufacturerProgress, setManufacturerProgress] = useState(0);
  const [modelProgress, setModelProgress] = useState(0);
  const [avgManufacturerTime, setAvgManufacturerTime] = useState(3500); // Default 3.5s
  const [avgModelTime, setAvgModelTime] = useState(3000); // Default 3s - similar regardless of count
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const loadTimesRef = useRef<{ manufacturers: number[], models: number[] }>({ 
    manufacturers: [], 
    models: [] 
  });

  useEffect(() => {
    // Only load manufacturers once
    loadManufacturers();
    // Remove the calculateAverageLoadTimes call - it's causing extra requests
    // calculateAverageLoadTimes();
    
    // Clean up session PDFs when the page unloads
    const handleBeforeUnload = () => {
      // Use sendBeacon for reliable cleanup on page unload
      const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
      const data = JSON.stringify({});
      navigator.sendBeacon(`${apiUrl}/api/clear-session-pdfs`, data);
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Cleanup on component unmount
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // Only clear session PDFs once on unmount using deduplicated API
      api.clearSessionPdfs().catch(() => {});
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Removed calculateAverageLoadTimes - using hardcoded values for loading animations
  // avgManufacturerTime defaults to 3500ms
  // avgModelTime defaults to 3000ms

  const startProgress = (type: 'manufacturer' | 'model', duration: number) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    
    const setProgress = type === 'manufacturer' ? setManufacturerProgress : setModelProgress;
    setProgress(0);
    
    const interval = 50; // Update every 50ms for smooth animation
    const linearPhaseEnd = 80; // Linear progress up to 80%
    const linearDuration = duration * 1.3; // Slow down by 30% (multiply by 1.3)
    let elapsed = 0;
    
    progressIntervalRef.current = setInterval(() => {
      elapsed += interval;
      
      if (elapsed <= linearDuration) {
        // Linear phase: 0% to 80% (now 30% slower)
        const linearProgress = (elapsed / linearDuration) * linearPhaseEnd;
        setProgress(linearProgress);
      } else {
        // Logarithmic phase: 80% to ~99.9%
        // Using exponential decay: progress = 100 - 20 * e^(-k * t)
        // Where k controls the rate of slowdown
        const timeInLogPhase = elapsed - linearDuration;
        const k = 0.0008; // Decay constant - smaller = slower approach to 100%
        const logProgress = 100 - 20 * Math.exp(-k * timeInLogPhase);
        setProgress(Math.min(logProgress, 99.9)); // Never quite reach 100%
      }
    }, interval);
  };

  const completeProgress = (type: 'manufacturer' | 'model') => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    const setProgress = type === 'manufacturer' ? setManufacturerProgress : setModelProgress;
    
    // Smoothly animate from current position to 100%
    let current = type === 'manufacturer' ? manufacturerProgress : modelProgress;
    const startProgress = current;
    const targetProgress = 100;
    const animationDuration = 200; // 200ms for the final animation
    const interval = 20;
    const steps = animationDuration / interval;
    const increment = (targetProgress - startProgress) / steps;
    let step = 0;
    
    const completeInterval = setInterval(() => {
      step++;
      if (step >= steps) {
        setProgress(100);
        clearInterval(completeInterval);
        // Reset after a short delay
        setTimeout(() => setProgress(0), 400);
      } else {
        // Use easing for smoother animation
        const progress = startProgress + (increment * step);
        setProgress(progress);
      }
    }, interval);
  };

  const loadManufacturers = async () => {
    // Prevent duplicate calls
    if (loadingManufacturers) {
      console.log('Already loading manufacturers, skipping duplicate call');
      return;
    }
    
    const startTime = Date.now();
    setLoadingManufacturers(true);
    setError(null);
    startProgress('manufacturer', avgManufacturerTime);
    
    try {
      const data = await api.getManufacturers();
      // Filter out manufacturers with no models
      const filteredData = data.filter((mfg: any) => mfg.modelCount > 0);
      console.log(`Filtered manufacturers: ${filteredData.length} of ${data.length} have models`);
      setManufacturers(filteredData);
      
      // Update average time
      const loadTime = Date.now() - startTime;
      loadTimesRef.current.manufacturers.push(loadTime);
      if (loadTimesRef.current.manufacturers.length > 5) {
        loadTimesRef.current.manufacturers.shift();
      }
      const newAvg = loadTimesRef.current.manufacturers.reduce((a, b) => a + b, 0) / loadTimesRef.current.manufacturers.length;
      setAvgManufacturerTime(Math.max(newAvg, 2500));
    } catch (error: any) {
      setError(error.message || 'Failed to load manufacturers');
    } finally {
      completeProgress('manufacturer');
      setLoadingManufacturers(false);
    }
  };

  const handleManufacturerChange = async (event: SelectChangeEvent) => {
    const manufacturerId = event.target.value;
    
    // If we're on the detail page, clear PDFs and go back to list
    if (currentPage === 'detail') {
      const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
      await fetch(`${apiUrl}/api/clear-session-pdfs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      }).catch(err => console.log('Failed to clear PDFs:', err));
      setCurrentPage('list');
      setSelectedManual(null);
      setManualMetadata(null);
    }
    
    setSelectedManufacturer(manufacturerId);
    setSelectedModel('');
    setModels([]);
    setManuals([]);
    
    if (!manufacturerId) return;
    
    // Prevent duplicate requests for the same manufacturer
    if (activeModelRequest.current === manufacturerId) {
      console.log(`Already loading models for ${manufacturerId}, skipping duplicate`);
      return;
    }
    
    activeModelRequest.current = manufacturerId;
    const startTime = Date.now();
    setLoadingModels(true);
    setError(null);
    startProgress('model', avgModelTime);
    
    try {
      const data = await api.getModels(manufacturerId);
      // Only update if this is still the active request
      if (activeModelRequest.current === manufacturerId) {
        setModels(data);
      }
      
      // Update average time for models
      const loadTime = Date.now() - startTime;
      loadTimesRef.current.models.push(loadTime);
      if (loadTimesRef.current.models.length > 5) {
        loadTimesRef.current.models.shift();
      }
      if (loadTimesRef.current.models.length > 0) {
        const newAvg = loadTimesRef.current.models.reduce((a, b) => a + b, 0) / loadTimesRef.current.models.length;
        setAvgModelTime(Math.max(newAvg, 2500)); // Consistent time regardless of model count
      }
    } catch (error: any) {
      if (activeModelRequest.current === manufacturerId) {
        setError(error.message || 'Failed to load models');
      }
    } finally {
      if (activeModelRequest.current === manufacturerId) {
        completeProgress('model');
        setLoadingModels(false);
        activeModelRequest.current = null;
      }
    }
  };

  const handleModelChange = async (event: SelectChangeEvent) => {
    const modelId = event.target.value;
    
    // If we're on the detail page, clear PDFs and go back to list
    if (currentPage === 'detail') {
      const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
      await fetch(`${apiUrl}/api/clear-session-pdfs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      }).catch(err => console.log('Failed to clear PDFs:', err));
      setCurrentPage('list');
      setSelectedManual(null);
      setManualMetadata(null);
    }
    
    setSelectedModel(modelId);
    setManuals([]);
    
    if (!modelId || !selectedManufacturer) return;
    
    const model = models.find(m => m.id === modelId);
    
    if (model?.manuals && model.manuals.length > 0) {
      setManuals(model.manuals);
    } else {
      setLoadingManuals(true);
      setError(null);
      try {
        const data = await api.getManuals(selectedManufacturer, modelId);
        setManuals(data);
      } catch (error: any) {
        setError(error.message || 'Failed to load manuals');
        setManuals([]);
      } finally {
        setLoadingManuals(false);
      }
    }
  };

  const handleReset = () => {
    setSelectedManufacturer('');
    setSelectedModel('');
    setModels([]);
    setManuals([]);
    setError(null);
    setSelectedManual(null);
    setCurrentPage('list');
    
    // Clear session PDFs on reset using deduplicated API call
    api.clearSessionPdfs().catch(err => console.log('Failed to clear session PDFs:', err));
  };

  const handleManualClick = async (manual: Manual) => {
    // Clear any existing PDFs before loading a new one
    if (currentPage === 'detail') {
      const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
      await fetch(`${apiUrl}/api/clear-session-pdfs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      }).catch(err => console.log('Failed to clear previous PDFs:', err));
    }
    
    setSelectedManual(manual);
    setCurrentPage('detail');
    setManualMetadata(null);
    setLoadingMetadata(true);
    
    // Fetch metadata from backend
    try {
      const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
      const response = await fetch(`${apiUrl}/api/manual-metadata?url=${encodeURIComponent(manual.url)}&manufacturer_id=${encodeURIComponent(selectedManufacturer || '')}&model_id=${encodeURIComponent(selectedModel || '')}`, {
        credentials: 'include' // Include cookies for session
      });
      if (response.ok) {
        const data = await response.json();
        setManualMetadata(data);
      }
    } catch (error) {
      console.error('Failed to fetch manual metadata:', error);
    } finally {
      setLoadingMetadata(false);
    }
  };

  const handleBackToList = () => {
    setCurrentPage('list');
    setSelectedManual(null);
    
    // Always clear the session PDFs when going back from detail page
    const apiUrl = window.location.hostname === 'localhost' ? 'http://localhost:8888' : '';
    fetch(`${apiUrl}/api/clear-session-pdfs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Include cookies for session
    }).catch(err => console.log('Failed to clear session PDFs:', err));
  };

  // Unused function - keeping for potential future use
  // const getManualIcon = (type: string) => {
  //   const lowerType = type.toLowerCase();
  //   if (lowerType.includes('service')) return '🔧';
  //   if (lowerType.includes('parts')) return '🔩';
  //   if (lowerType.includes('wiring')) return '⚡';
  //   if (lowerType.includes('installation')) return '📦';
  //   if (lowerType.includes('operation')) return '📖';
  //   return '📄';
  // };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        minHeight: '100vh',
        backgroundColor: 'background.default'
      }}>
        <AppBar position="sticky" elevation={1} sx={{ backgroundColor: '#D32F2F' }}>
          <Toolbar sx={{ minHeight: { xs: 56, sm: 64 } }}>
            {currentPage === 'detail' ? (
              <IconButton
                onClick={handleBackToList}
                sx={{
                  color: 'white',
                  mr: 1,
                  '&:hover': {
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <ArrowBack sx={{ fontSize: 28 }} />
              </IconButton>
            ) : (
              <Box
                component="img"
                src="/logo.jpg"
                alt="Manual Processor"
                sx={{
                  height: { xs: 32, sm: 40 },
                  mr: 2,
                }}
              />
            )}
            <Typography 
              variant="h6" 
              component="div" 
              sx={{ 
                flexGrow: 1,
                fontSize: { xs: '1rem', sm: '1.25rem' },
                fontWeight: 600,
                color: 'white'
              }}
            >
              Manual Processor
            </Typography>
            <Button
              color="inherit"
              size="small"
              startIcon={<Refresh />}
              onClick={handleReset}
              sx={{ display: selectedManufacturer && currentPage === 'list' ? 'flex' : 'none' }}
            >
              Reset
            </Button>
          </Toolbar>
        </AppBar>

        <Container maxWidth="md" sx={{ py: { xs: 2, sm: 3 }, flexGrow: 1 }}>
          {currentPage === 'list' ? (
            <>
              <Card 
                elevation={1} 
                sx={{ 
                  mb: { xs: 2, sm: 3 },
                  borderRadius: 1,
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              >
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Typography 
                    variant="h4" 
                    gutterBottom 
                    sx={{ 
                      fontWeight: 700,
                      mb: 1
                    }}
                  >
                    Find Your Manual
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Select your equipment manufacturer and model to access technical documentation
                  </Typography>
                </CardContent>
              </Card>

          {error && (
            <Alert 
              severity="error" 
              sx={{ mb: 2 }} 
              onClose={() => setError(null)}
            >
              {error}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Manufacturer Dropdown */}
            <Box sx={{ position: 'relative' }}>
              <FormControl fullWidth variant="outlined">
                <InputLabel id="manufacturer-label">
                  {loadingManufacturers ? 'Loading manufacturers...' : 'Select Manufacturer'}
                </InputLabel>
                <Select
                  labelId="manufacturer-label"
                  value={selectedManufacturer}
                  onChange={handleManufacturerChange}
                  label={loadingManufacturers ? 'Loading manufacturers...' : 'Select Manufacturer'}
                  disabled={loadingManufacturers}
                  sx={{ 
                    backgroundColor: 'white',
                    '& .MuiSelect-select': {
                      py: 1.5
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#CC0000',
                    }
                  }}
                >
                  <MenuItem value="">
                    <em>Choose a manufacturer...</em>
                  </MenuItem>
                  {manufacturers.map((manufacturer) => (
                    <MenuItem key={manufacturer.id} value={manufacturer.id}>
                      <Box sx={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        width: '100%',
                        alignItems: 'center'
                      }}>
                        <Typography>{manufacturer.name}</Typography>
                        <Chip 
                          label={`${manufacturer.modelCount} models`} 
                          size="small" 
                          variant="outlined"
                          sx={{ ml: 2 }}
                        />
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                {loadingManufacturers && manufacturerProgress > 0 && (
                  <LinearProgress 
                    variant="determinate" 
                    value={manufacturerProgress} 
                    sx={{ 
                      position: 'absolute',
                      bottom: 1,
                      left: '1.5%',
                      width: '97%',
                      height: 2,
                      borderRadius: '0 0 3px 3px',
                      backgroundColor: 'rgba(211, 47, 47, 0.1)',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: '#D32F2F',
                        transition: 'transform 0.2s ease-out',
                        borderRadius: '0 0 3px 3px',
                      }
                    }}
                  />
                )}
              </FormControl>
            </Box>

            {/* Model Dropdown */}
            <Box sx={{ position: 'relative' }}>
              <FormControl 
                fullWidth 
                variant="outlined" 
                disabled={!selectedManufacturer || loadingModels}
              >
                <InputLabel id="model-label">
                  {loadingModels ? 'Loading models...' : 'Select Model'}
                </InputLabel>
                <Select
                  labelId="model-label"
                  value={selectedModel}
                  onChange={handleModelChange}
                  label={loadingModels ? 'Loading models...' : 'Select Model'}
                  sx={{ 
                    backgroundColor: 'white',
                    '& .MuiSelect-select': {
                      py: 1.5
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#CC0000',
                    }
                  }}
                >
                  <MenuItem value="">
                    <em>Choose a model...</em>
                  </MenuItem>
                  {models.map((model) => (
                    <MenuItem key={model.id} value={model.id}>
                      <Box sx={{ width: '100%' }}>
                        <Typography>{model.name}</Typography>
                        {model.description && (
                          <Typography variant="caption" color="text.secondary">
                            {model.description.substring(0, 50)}...
                          </Typography>
                        )}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
                {loadingModels && modelProgress > 0 && (
                  <LinearProgress 
                    variant="determinate" 
                    value={modelProgress} 
                    sx={{ 
                      position: 'absolute',
                      bottom: 1,
                      left: '1.5%',
                      width: '97%',
                      height: 2,
                      borderRadius: '0 0 3px 3px',
                      backgroundColor: 'rgba(211, 47, 47, 0.1)',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: '#D32F2F',
                        transition: 'transform 0.2s ease-out',
                        borderRadius: '0 0 3px 3px',
                      }
                    }}
                  />
                )}
              </FormControl>
            </Box>

            {/* Loading States */}
            {loadingManufacturers && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {loadingModels && (
              <Box sx={{ py: 2 }}>
                <Skeleton variant="rectangular" height={56} sx={{ borderRadius: 1 }} />
              </Box>
            )}


            {/* Manuals List - Simplified */}
            {manuals.length > 0 && (
              <>
                <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                  <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      Available Manuals ({manuals.length})
                    </Typography>
                  </Box>
                  <List sx={{ p: 0 }}>
                    {manuals.map((manual, index) => (
                      <ListItem
                        key={index}
                        onClick={() => handleManualClick(manual)}
                        sx={{
                          borderBottom: index < manuals.length - 1 ? '1px solid' : 'none',
                          borderColor: 'divider',
                          py: 2,
                          cursor: 'pointer',
                          '&:hover': {
                            backgroundColor: 'action.hover',
                          },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 36 }}>
                          <DescriptionIcon sx={{ fontSize: 20, color: 'text.secondary' }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Typography variant="body1">
                              {manual.title || manual.type}
                            </Typography>
                          }
                          secondary={
                            <Typography variant="caption" color="text.secondary">
                              {manual.format || 'PDF'} {manual.language && `• ${manual.language.toUpperCase()}`}
                            </Typography>
                          }
                        />
                        <ChevronRight sx={{ color: 'text.secondary' }} />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
                
                {/* PartsTown Link Button */}
                {selectedManufacturer && selectedModel && (
                  <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
                    <Button
                      variant="outlined"
                      startIcon={<OpenInNew />}
                      onClick={() => {
                        // Get manufacturer URI from the manufacturer data
                        const manufacturer = manufacturers.find(m => m.id === selectedManufacturer);
                        if (manufacturer?.uri) {
                          const partstownUrl = `https://www.partstown.com/${manufacturer.uri}/${selectedModel}/parts`;
                          window.open(partstownUrl, '_blank');
                        }
                      }}
                      sx={{ 
                        borderColor: 'divider',
                        color: 'text.secondary',
                        '&:hover': {
                          borderColor: 'primary.main',
                          backgroundColor: 'action.hover',
                        }
                      }}
                    >
                      View on PartsTown
                    </Button>
                  </Box>
                )}
              </>
            )}

            {loadingManuals && (
              <Box sx={{ py: 2 }}>
                <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 1 }} />
              </Box>
            )}

            {selectedModel && !loadingManuals && manuals.length === 0 && (
              <>
                <Alert severity="info">
                  No manuals available for this model. Please try another model or contact support.
                </Alert>
                
                {/* PartsTown Link Button for no manuals case */}
                {selectedManufacturer && (
                  <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
                    <Button
                      variant="outlined"
                      startIcon={<OpenInNew />}
                      onClick={() => {
                        const manufacturer = manufacturers.find(m => m.id === selectedManufacturer);
                        if (manufacturer?.uri) {
                          const partstownUrl = `https://www.partstown.com/${manufacturer.uri}/${selectedModel}/parts`;
                          window.open(partstownUrl, '_blank');
                        }
                      }}
                      sx={{ 
                        borderColor: 'divider',
                        color: 'text.secondary',
                        '&:hover': {
                          borderColor: 'primary.main',
                          backgroundColor: 'action.hover',
                        }
                      }}
                    >
                      View on PartsTown
                    </Button>
                  </Box>
                )}
              </>
            )}
          </Box>
            </>
          ) : (
            /* Manual Detail Page */
            <Box>
              {selectedManual && (
                <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                  {/* Make and Model */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                      {manufacturers.find(m => m.id === selectedManufacturer)?.name || 'Unknown Manufacturer'}
                    </Typography>
                    <Typography variant="h6" color="text.secondary">
                      {models.find(m => m.id === selectedModel)?.name || 'Unknown Model'}
                    </Typography>
                  </Box>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  {/* Filename and Manual Type */}
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      MANUAL TYPE
                    </Typography>
                    <Typography variant="body1" sx={{ fontWeight: 500, mb: 2 }}>
                      {selectedManual.title || selectedManual.type}
                    </Typography>
                    
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      FILENAME
                    </Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.9rem', mb: 2 }}>
                      {selectedManual.url.split('/').pop() || 'manual.pdf'}
                    </Typography>
                    
                    {/* Link to Local PDF */}
                    {manualMetadata?.localUrl && (
                      <>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          LOCAL COPY
                        </Typography>
                        <Button
                          variant="contained"
                          color="primary"
                          href={manualMetadata.localUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          startIcon={<PictureAsPdf />}
                        >
                          Open PDF
                        </Button>
                      </>
                    )}
                  </Box>

                  <Divider sx={{ my: 3 }} />
                  
                  {/* PDF Metadata */}
                  <Typography variant="h6" gutterBottom>
                    Document Information
                  </Typography>
                  
                  {loadingMetadata ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2 }}>
                      <CircularProgress size={20} />
                      <Typography variant="body2" color="text.secondary">
                        Downloading and analyzing PDF...
                      </Typography>
                    </Box>
                  ) : manualMetadata ? (
                    <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 2, mt: 2 }}>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          PAGE COUNT
                        </Typography>
                        <Typography variant="h6">
                          {manualMetadata.pageCount || 'N/A'} pages
                        </Typography>
                      </Paper>
                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          FILE SIZE
                        </Typography>
                        <Typography variant="h6">
                          {manualMetadata.fileSize || 'N/A'}
                        </Typography>
                      </Paper>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Metadata will be loaded when available
                    </Typography>
                  )}
                  
                  {/* PDF Preview */}
                  {manualMetadata?.preview && (
                    <>
                      <Divider sx={{ my: 3 }} />
                      <Typography variant="h6" gutterBottom>
                        Preview (First Page)
                      </Typography>
                      <Paper 
                        variant="outlined" 
                        sx={{ 
                          mt: 2, 
                          p: 2, 
                          backgroundColor: 'grey.50',
                          display: 'flex',
                          justifyContent: 'center',
                          overflow: 'auto',
                          maxHeight: '600px'
                        }}
                      >
                        <img 
                          src={manualMetadata.preview} 
                          alt="PDF Preview" 
                          style={{ 
                            maxWidth: '100%',
                            height: 'auto',
                            boxShadow: '0 4px 8px rgba(0,0,0,0.1)'
                          }}
                        />
                      </Paper>
                    </>
                  )}
                  
                  <Box sx={{ p: 3, backgroundColor: 'grey.50', borderRadius: 1, mt: 3 }}>
                    <Typography variant="body2" color="text.secondary" align="center">
                      Coming soon: AI-powered manual analysis, step-by-step extraction, and interactive documentation
                    </Typography>
                  </Box>
                </Paper>
              )}
            </Box>
          )}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;