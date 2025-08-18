import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActionArea,
  Typography,
  TextField,
  Box,
  Chip,
  InputAdornment,
} from '@mui/material';
import { Search, Factory } from '@mui/icons-material';
import { Manufacturer } from '../types';

interface ManufacturerSelectorProps {
  manufacturers: Manufacturer[];
  onSelect: (manufacturer: Manufacturer) => void;
  selected: Manufacturer | null;
}

const ManufacturerSelector: React.FC<ManufacturerSelectorProps> = ({
  manufacturers,
  onSelect,
  selected,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredManufacturers = manufacturers.filter((m) =>
    m.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Box>
      <TextField
        fullWidth
        variant="outlined"
        placeholder="Search manufacturers..."
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

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {filteredManufacturers.length} manufacturers found
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        {filteredManufacturers.map((manufacturer) => (
          <Box
            key={manufacturer.id}
            sx={{
              width: { xs: '100%', sm: 'calc(50% - 8px)', md: 'calc(33.333% - 11px)', lg: 'calc(25% - 12px)' },
            }}
          >
            <Card
              elevation={selected?.id === manufacturer.id ? 3 : 1}
              sx={{
                height: '100%',
                borderColor: selected?.id === manufacturer.id ? 'primary.main' : 'divider',
                borderWidth: selected?.id === manufacturer.id ? 2 : 1,
                borderStyle: 'solid',
                transition: 'all 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: 3,
                },
              }}
            >
              <CardActionArea
                onClick={() => onSelect(manufacturer)}
                sx={{ height: '100%' }}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Factory sx={{ fontSize: 20, mr: 1, color: 'primary.main' }} />
                    <Typography
                      variant="h6"
                      component="div"
                      sx={{
                        fontSize: '1rem',
                        fontWeight: 600,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {manufacturer.name}
                    </Typography>
                  </Box>
                  <Chip
                    label={`${manufacturer.modelCount} models`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </CardContent>
              </CardActionArea>
            </Card>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default ManufacturerSelector;