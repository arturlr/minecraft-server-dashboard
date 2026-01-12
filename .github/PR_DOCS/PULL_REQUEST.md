# Pull Request: Code Quality Improvements - Linting, Formatting, and Test Fixes

## Summary

This PR implements comprehensive code quality improvements across the entire codebase, including:
- ✅ Automated linting and formatting for Vue.js/JavaScript code
- ✅ Automated Python code formatting (Black) for Lambda functions
- ✅ Fixed critical test issues (mock initialization)
- ✅ Removed unused variables and imports
- ✅ Added linting configurations for consistent code style
- ✅ Docker environment for development and testing

## Changes Made

### 1. Frontend Linting Setup (Dashboard & Webapp)

#### New Configuration Files
- **`dashboard/eslint.config.js`** - ESLint configuration for dashboard Vue.js app
- **`webapp/eslint.config.js`** - ESLint configuration for webapp Vue.js app
- Configured with Vue 3 best practices
- Disabled overly strict formatting rules (prefer auto-formatting)
- Added browser and Vitest globals

#### ESLint Results
- **Dashboard**: Reduced from **initial state** to **0 errors, 51 warnings**
- **Webapp**: Reduced to **0 errors, 9 warnings**
- All critical errors fixed

### 2. Backend Python Formatting

#### New Configuration Files
- **`setup.cfg`** - Flake8 and PyLint configuration
- **`pyproject.toml`** - Black formatter configuration (Python 3.13)

#### Python Formatting Results
- ✅ Formatted **25 Python files** with Black (120 char line length)
- ✅ Reduced Flake8 issues to **6 warnings** (mainly test files)
- ✅ Consistent code style across all Lambda functions and layers

### 3. Test Improvements

#### Fixed Critical Mock Initialization Issues
**Problem**: Tests were failing with "Cannot access 'mockGraphQLClient' before initialization"

**Solution**: Used `vi.hoisted()` to properly hoist mock definitions before module imports

**Files Fixed**:
- `dashboard/src/__tests__/ServerCreationE2E.test.js`
- `dashboard/src/components/__tests__/ServerCreationIntegration.test.js`
- `dashboard/src/views/__tests__/HomeView.integration.test.js`

#### Test Results
- **Before**: 7 failed test files, 29 passing tests
- **After**: 6 failed test files, 45 passing tests
- **Improvement**: +16 passing tests (55% increase)

### 4. Code Cleanup

#### Removed Unused Variables/Imports
- `dashboard/src/__tests__/ServerCreationE2E.test.js` - Removed unused `serverName` variable
- `dashboard/src/components/CreateServerDialog.vue` - Removed unused `parseError` variable
- `dashboard/src/components/PowerControlDialog.vue` - Removed unused `isRetryableError` and `serverStore` imports
- `lambdas/serverAction/test_get_server_users.py` - Removed unused `MagicMock` and `json` imports
- `lambdas/serverActionProcessor/test_create_server_basic.py` - Removed unused imports, fixed comparison operator

#### Fixed Switch Statement Issues
- `dashboard/src/views/AuthView.vue` - Wrapped case blocks in braces to fix lexical declaration errors

### 5. Docker Development Environment

#### New Files
- **`Dockerfile`** - Multi-stage Node.js + Python development environment
- **`.dockerignore`** - Optimized Docker build context

#### Features
- Node.js 20 Alpine base image
- Python 3.12 with linting tools (flake8, pylint, black, autopep8)
- ESLint and Prettier installed globally
- Separate dependency installation for dashboard and webapp
- Optimized layer caching

## Testing Instructions

### Run Linters

```bash
# JavaScript/Vue linting (Dashboard)
cd dashboard
npm install
npx eslint "src/**/*.{js,vue}"

# JavaScript/Vue linting (Webapp)
cd webapp
npm install
npx eslint "src/**/*.{js,vue}"

# Python linting
flake8 lambdas/ layers/
black --check lambdas/ layers/
```

### Run Tests

```bash
# Unit tests (Vitest)
cd dashboard
npm test

# E2E tests (Playwright)
cd dashboard
npm run test:e2e
```

### Using Docker

```bash
# Build Docker image
docker build -t minecraft-dashboard:dev .

# Run linters in Docker
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npx eslint "src/**/*.{js,vue}"

# Run tests in Docker
docker run --rm -v $(pwd)/dashboard:/app/dashboard -w /app/dashboard minecraft-dashboard:dev npm test

# Format Python code in Docker
docker run --rm -v $(pwd):/app -w /app minecraft-dashboard:dev black lambdas/ layers/
```

## Breaking Changes

⚠️ **None** - This PR only improves code quality without changing functionality.

## Notes for Reviewers

### Linting Warnings (Non-Critical)
The remaining ESLint warnings are mostly:
- Unused props/variables in test files (acceptable for test mocks)
- Template shadow variables (Vuetify patterns with scoped slots)
- V-slot style preferences (existing Vuetify syntax)

These can be addressed in follow-up PRs if desired.

### Test Failures
The 6 remaining test failures are related to:
- Playwright tests requiring authentication setup
- Missing Vuetify component mocks in integration tests

These are **pre-existing issues** not introduced by this PR. The mock initialization fixes actually **improved** the test pass rate from 29 to 45 passing tests.

### Python Linting
The 6 remaining Flake8 warnings are in test files:
- Unused imports in test setup (common pattern)
- Unused variables in assertion tests

These are acceptable patterns in test code.

## Configuration Files Added

1. `dashboard/eslint.config.js` - Dashboard ESLint rules
2. `webapp/eslint.config.js` - Webapp ESLint rules
3. `setup.cfg` - Python Flake8/PyLint configuration
4. `pyproject.toml` - Black formatter configuration
5. `Dockerfile` - Development environment
6. `.dockerignore` - Docker build optimization

## Benefits

1. **Consistent Code Style**: All JavaScript/Vue and Python code follows consistent formatting
2. **Improved Test Reliability**: Fixed critical mock initialization issues
3. **Better Developer Experience**: Docker environment for consistent development across machines
4. **Easier Code Review**: Cleaner code with fewer unused variables and imports
5. **Future-Proof**: Linting configuration prevents introduction of new code quality issues

## CI/CD Considerations

These linters can be added to CI/CD pipeline:
```yaml
# Example GitHub Actions
- name: Lint JavaScript
  run: |
    cd dashboard && npm install && npx eslint "src/**/*.{js,vue}"
    cd ../webapp && npm install && npx eslint "src/**/*.{js,vue}"

- name: Lint Python
  run: |
    pip install flake8 black
    flake8 lambdas/ layers/
    black --check lambdas/ layers/
```

## Screenshots

N/A - No UI changes in this PR. All changes are code quality improvements.

---

**Checklist**:
- [x] Code formatted with Black (Python) and ESLint (JavaScript/Vue)
- [x] All linter errors fixed (0 errors in final state)
- [x] Tests updated and passing rate improved (+16 tests)
- [x] Docker environment tested and working
- [x] Configuration files documented
- [x] No breaking changes introduced
- [x] Ready for review

**Reviewers**: Please focus on:
1. Linting configuration appropriateness
2. Test fix correctness (vi.hoisted pattern)
3. Docker setup usability
4. Any remaining critical warnings that should be addressed
