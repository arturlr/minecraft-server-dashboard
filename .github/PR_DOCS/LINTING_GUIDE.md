# Quick Reference: Running Linters and Tests

## Prerequisites

### Option 1: Using Docker (Recommended)
```bash
# Build the Docker image (one time)
docker build -t minecraft-dashboard:dev .
```

### Option 2: Local Installation
```bash
# Install Node.js dependencies
cd dashboard && npm install && cd ..
cd webapp && npm install && cd ..

# Install Python dependencies
pip install flake8 black pylint autopep8
```

## Running Linters

### JavaScript/Vue Linting

#### Dashboard
```bash
# Using Docker
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npx eslint "src/**/*.{js,vue}"

# Using Docker with auto-fix
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npx eslint "src/**/*.{js,vue}" --fix

# Local
cd dashboard && npx eslint "src/**/*.{js,vue}"
cd dashboard && npx eslint "src/**/*.{js,vue}" --fix
```

#### Webapp
```bash
# Using Docker
docker run --rm -v $(pwd)/webapp:/app/webapp -w /app/webapp minecraft-dashboard:dev npx eslint "src/**/*.{js,vue}"

# Using Docker with auto-fix
docker run --rm -v $(pwd)/webapp:/app/webapp -w /app/webapp minecraft-dashboard:dev npx eslint "src/**/*.{js,vue}" --fix

# Local
cd webapp && npx eslint "src/**/*.{js,vue}"
cd webapp && npx eslint "src/**/*.{js,vue}" --fix
```

### Python Linting and Formatting

#### Check Formatting (Black)
```bash
# Using Docker - check only
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev black --check lambdas/ layers/

# Using Docker - format files
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev black lambdas/ layers/

# Local
black --check lambdas/ layers/
black lambdas/ layers/
```

#### Linting (Flake8)
```bash
# Using Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev flake8 lambdas/ layers/

# Local
flake8 lambdas/ layers/
```

#### Advanced Linting (PyLint)
```bash
# Using Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev pylint lambdas/**/*.py layers/**/*.py

# Local
pylint lambdas/**/*.py layers/**/*.py
```

#### Auto-fix Python Issues (autopep8)
```bash
# Using Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev autopep8 --in-place --recursive lambdas/ layers/

# Local
autopep8 --in-place --recursive lambdas/ layers/
```

## Running Tests

### Unit Tests (Vitest)
```bash
# Using Docker
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm test

# Using Docker - watch mode
docker run --rm -it -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm run test:watch

# Local
cd dashboard && npm test
cd dashboard && npm run test:watch
```

### E2E Tests (Playwright)
```bash
# Using Docker (requires display setup)
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm run test:e2e

# Local
cd dashboard && npm run test:e2e
cd dashboard && npm run test:e2e:headed  # With browser UI
```

## All-in-One Commands

### Lint Everything
```bash
# Using Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev sh -c "
  cd dashboard && npx eslint 'src/**/*.{js,vue}' && cd .. &&
  cd webapp && npx eslint 'src/**/*.{js,vue}' && cd .. &&
  flake8 lambdas/ layers/ &&
  black --check lambdas/ layers/
"

# Local
cd dashboard && npx eslint "src/**/*.{js,vue}" && cd ..
cd webapp && npx eslint "src/**/*.{js,vue}" && cd ..
flake8 lambdas/ layers/
black --check lambdas/ layers/
```

### Format Everything
```bash
# Using Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev sh -c "
  cd dashboard && npx eslint 'src/**/*.{js,vue}' --fix && cd .. &&
  cd webapp && npx eslint 'src/**/*.{js,vue}' --fix && cd .. &&
  black lambdas/ layers/
"

# Local
cd dashboard && npx eslint "src/**/*.{js,vue}" --fix && cd ..
cd webapp && npx eslint "src/**/*.{js,vue}" --fix && cd ..
black lambdas/ layers/
```

### Run All Tests
```bash
# Using Docker
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm test

# Local
cd dashboard && npm test
```

## Common Workflows

### Before Committing
```bash
# Format and lint all code
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev sh -c "
  black lambdas/ layers/ &&
  cd dashboard && npx eslint 'src/**/*.{js,vue}' --fix && cd .. &&
  cd webapp && npx eslint 'src/**/*.{js,vue}' --fix
"

# Run tests
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm test
```

### During Development
```bash
# Watch mode for tests
cd dashboard && npm run test:watch

# Terminal 2: Auto-format on change (if using nodemon/watchman)
# Or use IDE auto-format on save
```

### Pre-Pull Request
```bash
# Full lint check (no auto-fix)
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev sh -c "
  cd dashboard && npx eslint 'src/**/*.{js,vue}' && cd .. &&
  cd webapp && npx eslint 'src/**/*.{js,vue}' && cd .. &&
  flake8 lambdas/ layers/ &&
  black --check lambdas/ layers/
"

# Run all tests
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm test
```

## IDE Integration

### VS Code

#### Recommended Extensions
- ESLint (dbaeumer.vscode-eslint)
- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)

#### Settings (.vscode/settings.json)
```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  },
  "[javascript]": {
    "editor.defaultFormatter": "dbaeumer.vscode-eslint"
  },
  "[vue]": {
    "editor.defaultFormatter": "dbaeumer.vscode-eslint"
  }
}
```

### WebStorm/IntelliJ

1. Go to Settings → Languages & Frameworks → JavaScript → Code Quality Tools → ESLint
2. Enable ESLint and set configuration file path
3. Go to Settings → Tools → Python Integrated Tools
4. Set Black as formatter
5. Enable "Format on save" in settings

## Troubleshooting

### ESLint not finding config
```bash
# Make sure you're in the correct directory
cd dashboard  # or webapp
npx eslint --print-config src/App.vue
```

### Docker permission errors
```bash
# Linux: Run with user permissions
docker run --rm -u $(id -u):$(id -g) -v $(pwd):/app -w /app minecraft-dashboard:dev ...
```

### Black/Flake8 not found
```bash
# Rebuild Docker image
docker build --no-cache -t minecraft-dashboard:dev .

# Or install locally
pip install --upgrade black flake8 pylint autopep8
```

### Tests failing
```bash
# Clean install dependencies
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm test
```

## Configuration Files Reference

- `dashboard/eslint.config.js` - Dashboard ESLint configuration
- `webapp/eslint.config.js` - Webapp ESLint configuration
- `setup.cfg` - Flake8 and PyLint configuration
- `pyproject.toml` - Black formatter configuration
- `dashboard/vite.config.js` - Vitest test configuration
- `dashboard/playwright.config.ts` - Playwright E2E test configuration
