# Minimalist Dashboard Redesign

## Design Changes Implemented

### Color Palette
- **Light theme**: White (#ffffff) surfaces on off-white (#fafafa) background
- **Dark theme**: Dark gray (#262626) surfaces on near-black (#171717) background
- **Accent**: Subtle green (#10b981) for status indicators only
- **Text**: Near-black (#171717) primary, gray (#737373) secondary
- **Borders**: Light gray (#e5e5e5) for subtle separation

### Typography Hierarchy
- **System fonts**: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto
- **Weight-based hierarchy**: 300 (light) for large numbers, 500 (medium) for headings, 600 (semibold) for emphasis
- **Size scale**: 36px stats → 24px metrics → 18px titles → 14px body → 13px labels → 11px micro

### Layout & Spacing
- **Generous whitespace**: 24-48px between major sections
- **Consistent padding**: 24px cards, 48px page margins
- **Max width**: 1200px content area for optimal readability
- **Grid**: 2-column layout for server cards on large screens

### Components Redesigned

#### Stats Cards
- Removed card backgrounds and borders
- Typography-only design with bottom border separator
- Large light-weight numbers (36px, font-weight 300)
- Small uppercase labels (13px, letter-spacing 0.5px)

#### Server Cards
- Flat white cards with subtle 1px border
- Removed hero images and gradients
- Status indicated by small 6px dot (green/gray/orange)
- Minimal icon buttons (power, settings)
- 2x2 metrics grid with inline sparklines
- Clean monospace font for IP addresses

#### Sparklines
- Single stroke line only (no fill, no area)
- Thin 1.5px stroke weight
- Reduced opacity (0.6) for subtlety
- No grid lines or axes

#### Sidebar
- Narrow 200px width
- Simple text-based navigation
- Minimal logo (32px square with initials)
- Active state: solid black background
- Hover state: light gray background

#### Header
- Single line title with bottom border
- No action buttons or notifications
- 24px font size, medium weight

### Removed Elements
- Hero images on server cards
- Gradient overlays
- Decorative icons
- Glow effects and shadows
- Access control section (simplified dashboard)
- Heavy card borders and backgrounds
- Notification badges
- "New Instance" button from header

### Accessibility
- Maintained WCAG AA contrast ratios
- Simplified visual hierarchy for screen readers
- Reduced motion (removed pulse animations)
- Clear focus states on interactive elements

### Performance
- Removed external image loading
- Simplified CSS (no complex gradients or shadows)
- Reduced DOM complexity
- Lighter font weights load faster

## Files Modified

1. `webapp/src/plugins/vuetify.js` - Light/dark theme configuration
2. `webapp/src/assets/styles/main.scss` - Global styles and system fonts
3. `webapp/src/components/dashboard/StatsCards.vue` - Typography-focused stats
4. `webapp/src/components/dashboard/ServerCard.vue` - Minimal server card
5. `webapp/src/components/common/SparkLine.vue` - Simple line charts
6. `webapp/src/components/layout/AppLayout.vue` - Clean layout structure
7. `webapp/src/components/layout/AppHeader.vue` - Minimal header
8. `webapp/src/components/layout/AppSidebar.vue` - Simple sidebar
9. `webapp/src/views/DashboardView.vue` - Simplified dashboard view

## Design Principles Applied

✓ Whitespace as a design element
✓ Limited color palette (neutral + green accent)
✓ Typography-driven hierarchy
✓ Flat, minimal UI elements
✓ Functional over decorative
✓ High contrast for accessibility
✓ Fast load times
✓ Scannable information architecture
