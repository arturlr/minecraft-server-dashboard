# Shutdown Configuration UI Improvements

## Overview
Enhanced the ServerSettings.vue component with better UX, visual feedback, and smart validation for shutdown configuration.

## Key Improvements

### 1. **Quick Schedule Presets** 🚀
- **Feature**: One-click presets for common schedules
- **Presets Available**:
  - Weekday Evenings (Mon-Fri, 5pm-11pm)
  - Weekend All Day (Sat-Sun, 8am-11pm)
  - Every Evening (All days, 6pm-11pm)
  - Business Hours (Mon-Fri, 9am-5pm)
- **Benefit**: Saves time and reduces configuration errors

### 2. **Smart Validation & Warnings** ⚠️

#### Schedule-Based Warnings:
- **Start > Stop Time**: Warns when start time is after stop time
- **Short Duration**: Alerts if server runs less than 1 hour
- **Runtime Display**: Shows exact hours/minutes server will run

#### Metric-Based Warnings:
- **High CPU Threshold**: Warns if CPU threshold > 20% (may cause premature shutdowns)
- **Short Evaluation**: Warns if evaluation period < 10 minutes for CPU
- **Connection Sensitivity**: Warns about brief disconnections with short periods

### 3. **Enhanced Visual Feedback** 🎨

#### Schedule Summary Card:
- **Visual Day Indicators**: Chips showing selected days (colored vs outlined)
- **Start/Stop Icons**: Green play icon for start, red stop icon for shutdown
- **Time Display**: Clear formatting with color-coded actions
- **Cron Expression**: Technical details in collapsible section

#### Metric Summary Card:
- **Condition Display**: Clear explanation of shutdown trigger
- **Visual Emphasis**: Color-coded thresholds and durations
- **Helpful Tips**: Context-specific recommendations

### 4. **Improved Layout** 📐
- **Better Spacing**: Consistent padding and margins
- **Card Hierarchy**: Clear visual separation between sections
- **Icon Usage**: Meaningful icons for quick recognition
- **Color Coding**:
  - Blue: Schedule configuration
  - Orange: Metric-based configuration
  - Green: Start actions
  - Red: Stop actions

### 5. **Better Information Architecture** 📊
- **Progressive Disclosure**: Show details only when relevant
- **Contextual Help**: Hints and tips based on selected method
- **Visual Hierarchy**: Important info stands out
- **Scannable Layout**: Easy to understand at a glance

## Technical Implementation

### New Computed Properties:
```javascript
scheduleWarning    // Validates schedule timing and duration
metricWarning      // Validates metric thresholds and periods
```

### New Functions:
```javascript
applyPreset(preset)  // Applies quick schedule presets
```

### New Data:
```javascript
schedulePresets     // Array of common schedule configurations
```

## User Benefits

1. **Faster Configuration**: Presets reduce setup time from minutes to seconds
2. **Fewer Errors**: Smart warnings prevent common misconfigurations
3. **Better Understanding**: Visual feedback makes complex settings clear
4. **Confidence**: Clear summaries show exactly what will happen
5. **Cost Awareness**: Runtime calculations help estimate savings

## Future Enhancements (Optional)

### Could Add:
- **Cost Estimator**: Show estimated monthly savings based on schedule
- **Timezone Selector**: Allow users to specify their timezone
- **Visual Calendar**: Weekly grid showing running hours
- **History**: Show past shutdown events and reasons
- **Templates**: Save custom presets for reuse
- **Conflict Detection**: Warn if schedule conflicts with peak usage times

## Example User Flows

### Flow 1: Quick Weekend Setup
1. Select "Schedule" shutdown method
2. Click "Weekend All Day" preset
3. Adjust times if needed
4. Save → Done in 10 seconds!

### Flow 2: CPU-Based with Validation
1. Select "% CPU" shutdown method
2. Enter threshold: 25%
3. See warning: "CPU threshold above 20% may cause premature shutdowns"
4. Adjust to 5%
5. Warning clears, shows helpful tip
6. Save with confidence

### Flow 3: Complex Schedule
1. Select "Schedule" shutdown method
2. Choose specific days (Mon, Wed, Fri)
3. Set start time: 17:00
4. Set stop time: 23:00
5. See visual summary with day chips
6. See runtime: "6h 0m per scheduled day"
7. Review cron expressions
8. Save

## Accessibility Improvements
- Clear labels and hints
- Color is not the only indicator (icons + text)
- Keyboard navigation friendly
- Screen reader compatible with ARIA labels

## Mobile Responsiveness
- Chips wrap on small screens
- Cards stack vertically
- Touch-friendly tap targets
- Readable text sizes
