import { useState, useEffect } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  Button,
  SelectChangeEvent,
  Paper
} from '@mui/material';

interface TimeRangeOption {
  label: string;
  value: string;
  startTime: () => Date;
  endTime: () => Date;
}

interface TimeRangeSelectorProps {
  onChange: (startTime: string, endTime: string) => void;
  defaultRange?: string;
}

const TIME_RANGES: TimeRangeOption[] = [
  {
    label: 'Last Hour',
    value: 'last_hour',
    startTime: () => new Date(Date.now() - 60 * 60 * 1000),
    endTime: () => new Date()
  },
  {
    label: 'Last 6 Hours',
    value: 'last_6_hours',
    startTime: () => new Date(Date.now() - 6 * 60 * 60 * 1000),
    endTime: () => new Date()
  },
  {
    label: 'Last 12 Hours',
    value: 'last_12_hours',
    startTime: () => new Date(Date.now() - 12 * 60 * 60 * 1000),
    endTime: () => new Date()
  },
  {
    label: 'Last 24 Hours',
    value: 'last_24_hours',
    startTime: () => new Date(Date.now() - 24 * 60 * 60 * 1000),
    endTime: () => new Date()
  },
  {
    label: 'Last 7 Days',
    value: 'last_7_days',
    startTime: () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    endTime: () => new Date()
  },
  {
    label: 'Custom Range',
    value: 'custom',
    startTime: () => new Date(Date.now() - 24 * 60 * 60 * 1000),
    endTime: () => new Date()
  }
];

/**
 * A component that allows users to select a time range from predefined options
 * or specify a custom range with date/time pickers.
 */
const TimeRangeSelector = ({ onChange, defaultRange = 'last_24_hours' }: TimeRangeSelectorProps) => {
  const [selectedRange, setSelectedRange] = useState(defaultRange);
  const [customStartTime, setCustomStartTime] = useState('');
  const [customEndTime, setCustomEndTime] = useState('');
  const [showCustomRange, setShowCustomRange] = useState(false);

  // Format date for datetime-local input
  const formatDateForInput = (date: Date): string => {
    return date.toISOString().slice(0, 16);
  };

  // Initialize custom date/time fields
  useEffect(() => {
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    setCustomStartTime(formatDateForInput(oneDayAgo));
    setCustomEndTime(formatDateForInput(now));
  }, []);

  // Handle range selection change
  const handleRangeChange = (event: SelectChangeEvent) => {
    const rangeValue = event.target.value;
    setSelectedRange(rangeValue);
    
    if (rangeValue === 'custom') {
      setShowCustomRange(true);
      // Keep existing custom range values
      onChange(new Date(customStartTime).toISOString(), new Date(customEndTime).toISOString());
    } else {
      setShowCustomRange(false);
      const selectedOption = TIME_RANGES.find(option => option.value === rangeValue);
      if (selectedOption) {
        onChange(
          selectedOption.startTime().toISOString(),
          selectedOption.endTime().toISOString()
        );
      }
    }
  };

  // Handle custom start time change
  const handleCustomStartChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCustomStartTime(event.target.value);
  };

  // Handle custom end time change
  const handleCustomEndChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setCustomEndTime(event.target.value);
  };

  // Apply custom range
  const handleApplyCustomRange = () => {
    onChange(
      new Date(customStartTime).toISOString(),
      new Date(customEndTime).toISOString()
    );
  };

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Grid container spacing={2} alignItems="flex-end">
        <Grid item xs={12} md={showCustomRange ? 4 : 12}>
          <FormControl fullWidth>
            <InputLabel id="time-range-select-label">Time Range</InputLabel>
            <Select
              labelId="time-range-select-label"
              id="time-range-select"
              value={selectedRange}
              label="Time Range"
              onChange={handleRangeChange}
            >
              {TIME_RANGES.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        {showCustomRange && (
          <>
            <Grid item xs={12} md={3}>
              <TextField
                label="Start Date/Time"
                type="datetime-local"
                value={customStartTime}
                onChange={handleCustomStartChange}
                fullWidth
                InputLabelProps={{
                  shrink: true,
                }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                label="End Date/Time"
                type="datetime-local"
                value={customEndTime}
                onChange={handleCustomEndChange}
                fullWidth
                InputLabelProps={{
                  shrink: true,
                }}
              />
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                variant="contained"
                onClick={handleApplyCustomRange}
                fullWidth
              >
                Apply
              </Button>
            </Grid>
          </>
        )}
      </Grid>
    </Paper>
  );
};

export default TimeRangeSelector; 