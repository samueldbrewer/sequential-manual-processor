import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActionArea,
  Typography,
  TextField,
  Box,
  Chip,
  Button,
  InputAdornment,
  Breadcrumbs,
  Link,
} from '@mui/material';
import { Search, Build, ArrowBack, Description, Factory } from '@mui/icons-material';
import { Model, Manufacturer } from '../types';

interface ModelSelectorProps {
  models: Model[];
  manufacturer: Manufacturer;
  onSelect: (model: Model) => void;
  onBack: () => void;
  selected: Model | null;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  models,
  manufacturer,
  onSelect,
  onBack,
  selected,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredModels = models.filter((m) =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (m.description && m.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Breadcrumbs aria-label="breadcrumb">
          <Link
            component="button"
            underline="hover"
            color="inherit"
            onClick={onBack}
            sx={{ display: 'flex', alignItems: 'center' }}
          >
            <Factory style={{ marginRight: 4, fontSize: 20 }} />
            Manufacturers
          </Link>
          <Typography color="text.primary">{manufacturer.name}</Typography>
        </Breadcrumbs>
      </Box>

      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search models..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
      />

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {filteredModels.length} models found
        </Typography>
        <Button startIcon={<ArrowBack />} onClick={onBack} variant="outlined" size="small">
          Back to Manufacturers
        </Button>
      </Box>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {filteredModels.map((model) => (
          <Box
            key={model.id}
            sx={{
              width: { xs: '100%', sm: 'calc(50% - 8px)', md: 'calc(33.333% - 11px)' },
            }}
          >
            <Card
              elevation={selected?.id === model.id ? 3 : 1}
              sx={{
                height: '100%',
                borderColor: selected?.id === model.id ? 'primary.main' : 'divider',
                borderWidth: selected?.id === model.id ? 2 : 1,
                borderStyle: 'solid',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 3,
                },
              }}
            >
              <CardActionArea
                onClick={() => onSelect(model)}
                sx={{ height: '100%' }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
                    <Build sx={{ fontSize: 20, mr: 1, color: 'primary.main', mt: 0.5 }} />
                    <Box sx={{ flex: 1 }}>
                      <Typography
                        variant="h6"
                        component="div"
                        sx={{
                          fontSize: '1rem',
                          fontWeight: 600,
                          mb: 0.5,
                        }}
                      >
                        {model.name}
                      </Typography>
                      {model.description && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            display: '-webkit-box',
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: 'vertical',
                            overflow: 'hidden',
                            minHeight: '2.5em',
                          }}
                        >
                          {model.description}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {model.manualCount !== undefined && model.manualCount > 0 && (
                      <Chip
                        icon={<Description sx={{ fontSize: 16 }} />}
                        label={`${model.manualCount} manual${model.manualCount > 1 ? 's' : ''}`}
                        size="small"
                        color="success"
                        variant="outlined"
                      />
                    )}
                    {model.manuals && model.manuals.length > 0 && (
                      <Chip
                        icon={<Description sx={{ fontSize: 16 }} />}
                        label={`${model.manuals.length} manual${model.manuals.length > 1 ? 's' : ''}`}
                        size="small"
                        color="success"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default ModelSelector;