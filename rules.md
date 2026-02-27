# CSS Refactoring Rules

## Overview

This file defines the design system rules that the CSS refactoring tool will apply to your codebase.

## Color Palette

### Primary Colors

```
--primary-blue: #2563eb
--primary-blue-dark: #1d4ed8
--primary-blue-light: #3b82f6
```

### Secondary Colors

```
--secondary-purple: #7c3aed
--secondary-green: #10b981
--secondary-red: #ef4444
```

### Neutral Colors

```
--gray-50: #f9fafb
--gray-100: #f3f4f6
--gray-200: #e5e7eb
--gray-300: #d1d5db
--gray-400: #9ca3af
--gray-500: #6b7280
--gray-600: #4b5563
--gray-700: #374151
--gray-800: #1f2937
--gray-900: #111827
```

### Semantic Colors

```
--success: #10b981
--warning: #f59e0b
--error: #ef4444
--info: #3b82f6
```

## Typography

### Font Families

```
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
--font-mono: 'Fira Code', 'Courier New', monospace
--font-serif: 'Merriweather', Georgia, serif
```

### Font Sizes

```
--text-xs: 0.75rem      /* 12px */
--text-sm: 0.875rem     /* 14px */
--text-base: 1rem       /* 16px */
--text-lg: 1.125rem     /* 18px */
--text-xl: 1.25rem      /* 20px */
--text-2xl: 1.5rem      /* 24px */
--text-3xl: 1.875rem    /* 30px */
--text-4xl: 2.25rem     /* 36px */
```

### Font Weights

```
--font-light: 300
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

### Line Heights

```
--leading-tight: 1.25
--leading-normal: 1.5
--leading-relaxed: 1.75
```

## Spacing

### Margin & Padding Scale

```
--space-0: 0
--space-1: 0.25rem      /* 4px */
--space-2: 0.5rem       /* 8px */
--space-3: 0.75rem      /* 12px */
--space-4: 1rem         /* 16px */
--space-5: 1.25rem      /* 20px */
--space-6: 1.5rem       /* 24px */
--space-8: 2rem         /* 32px */
--space-10: 2.5rem      /* 40px */
--space-12: 3rem        /* 48px */
--space-16: 4rem        /* 64px */
```

## Borders

### Border Widths

```
--border-0: 0
--border-1: 1px
--border-2: 2px
--border-4: 4px
```

### Border Radius

```
--rounded-none: 0
--rounded-sm: 0.125rem   /* 2px */
--rounded: 0.25rem       /* 4px */
--rounded-md: 0.375rem   /* 6px */
--rounded-lg: 0.5rem     /* 8px */
--rounded-xl: 0.75rem    /* 12px */
--rounded-2xl: 1rem      /* 16px */
--rounded-full: 9999px
```

## Shadows

### Box Shadows

```
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05)
--shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)
```

## Z-Index Scale

```
--z-0: 0
--z-10: 10
--z-20: 20
--z-30: 30
--z-40: 40
--z-50: 50
--z-modal: 1000
--z-dropdown: 1050
--z-tooltip: 1100
```

## Transitions

```
--transition-fast: 0.15s ease-in-out
--transition-base: 0.2s ease-in-out
--transition-slow: 0.3s ease-in-out
--transition-all: all 0.2s ease-in-out
```

## Additional Colors

```
--white: #ffffff
--black: #000000
--blue-50: #eff6ff
--blue-100: #dbeafe
--blue-200: #bfdbfe
--green-50: #ecfdf5
--green-100: #d1fae5
--red-50: #fef2f2
--red-100: #fee2e2
--yellow-50: #fefce8
--yellow-100: #fef9c3
--orange: #f59e0b
```

## Opacity Scale

```
--opacity-0: 0
--opacity-25: 0.25
--opacity-50: 0.5
--opacity-75: 0.75
--opacity-100: 1
```

## Breakpoints

```
--screen-sm: 640px
--screen-md: 768px
--screen-lg: 1024px
--screen-xl: 1280px
--screen-2xl: 1536px
```
