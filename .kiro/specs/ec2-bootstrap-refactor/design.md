# Design Document: EC2 Bootstrap Refactor

## Overview

The EC2 bootstrap SSM document currently contains duplicated package installation logic that makes the code harder to maintain and increases the risk of inconsistencies. This refactor will consolidate package installation into a unified, idempotent system that works across both RPM-based (Amazon Linux, RHEL, CentOS) and Debian-based (Ubuntu, Debian) distributions.

The current duplication exists between:
- `install_required_packages()` function: Handles Debian-based package installation with individual package checking
- `install_packages()` function: Contains inline package installation for RPM-based systems using `yum -y install "${REQUIRED_PACKAGES[@]}"`

Both functions install the same core packages: `jq`, `zip`, `unzip`, `net-tools`, `wget`, `screen`.

## Architecture

### Current Architecture Issues

The existing bootstrap script has several architectural problems:

1. **Package Installation Duplication**: The same package list is handled differently for RPM vs Debian systems
2. **Inconsistent Idempotency**: RPM systems don't check if packages are already installed before attempting installation
3. **Mixed Responsibilities**: The `install_packages()` function handles both CloudWatch agent installation and general package installation

### Proposed Architecture

The refactored architecture will implement a clean separation of concerns:

```
Bootstrap Script
├── Package Management Layer
│   ├── Unified Package List (REQUIRED_PACKAGES array)
│   ├── Distribution Detection (detect_distro)
│   └── Unified Package Installer (install_system_packages)
├── Specialized Installation Functions
│   ├── Java Installation (install_java)
│   ├── CloudWatch Agent Installation (install_cloudwatch)
│   └── AWS CLI Installation (install_awscli)
└── Main Orchestration (install_packages)
```

## Components and Interfaces

### 1. Unified Package Management

**Component**: `install_system_packages()`
- **Purpose**: Single function to handle installation of common utility packages across all distributions
- **Input**: Uses global `REQUIRED_PACKAGES` array
- **Output**: Success/failure status with logging
- **Behavior**: Idempotent - checks existing installations before attempting to install

**Interface**:
```bash
install_system_packages()
# Returns: 0 on success, 1 on failure
# Side effects: Installs missing packages, logs status
```

### 2. Distribution-Specific Package Checkers

**Component**: Package existence checking functions
- **Purpose**: Check if packages are already installed using distribution-appropriate commands
- **RPM Systems**: Use `rpm -q <package>` for individual package checking
- **Debian Systems**: Use `dpkg -l | grep "^ii.*<package> "` (existing implementation)

**Interface**:
```bash
is_package_installed() {
    local package=$1
    # Returns: 0 if installed, 1 if not installed
}
```

### 3. Specialized Installation Functions

**Components**: Existing specialized functions remain unchanged
- `install_java()` - Java installation with distribution detection
- `install_cloudwatch_rpm()` / `install_cloudwatch_deb()` - CloudWatch agent installation
- `install_awscli()` - AWS CLI installation

These functions maintain their current interfaces and responsibilities.

### 4. Main Orchestration Function

**Component**: Refactored `install_packages()`
- **Purpose**: Orchestrate all installation tasks with clear separation of concerns
- **Responsibilities**:
  1. Install system packages (delegated to `install_system_packages()`)
  2. Install CloudWatch agent (delegated to existing functions)
  3. Coordinate with other installation functions

## Data Models

### Package Configuration

```bash
# Global configuration - single source of truth
REQUIRED_PACKAGES=("jq" "zip" "unzip" "net-tools" "wget" "screen")
```

### Distribution Detection

```bash
# Existing detect_distro() function output
DISTRO_TYPES:
- "amzn" (Amazon Linux)
- "rhel" (Red Hat Enterprise Linux)  
- "centos" (CentOS)
- "ubuntu" (Ubuntu)
- "debian" (Debian)
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

<function_calls>
<invoke name="prework">
<parameter name="featureName">ec2-bootstrap-refactor

### Property 1: Unified Package Source
*For any* package installation operation, the system should reference the same REQUIRED_PACKAGES array regardless of distribution type
**Validates: Requirements 1.1**

### Property 2: Installation Idempotency
*For any* package in the required packages list, running the installation function multiple times should not fail if the package is already installed
**Validates: Requirements 1.2, 2.1**

### Property 3: Individual Package Checking on Debian
*For any* Debian-based system, the package installation function should check each package individually before attempting installation
**Validates: Requirements 1.3**

### Property 4: Distribution-Appropriate Commands
*For any* distribution type, the system should use the correct package manager commands (rpm/yum for RPM-based, dpkg/apt-get for Debian-based)
**Validates: Requirements 1.4, 2.2**

### Property 5: Successful Completion with Pre-installed Packages
*For any* system where all required packages are already installed, the bootstrap script should log the status and continue without errors
**Validates: Requirements 2.3**

### Property 6: Unified Package Installation Function
*For any* distribution type (RPM or Debian), the same install_system_packages function should be called for general utility package installation
**Validates: Requirements 3.4**

## Error Handling

### Package Installation Failures
- **Individual Package Failures**: If a single package fails to install, log the error but continue with remaining packages
- **Complete Installation Failure**: If package manager commands fail entirely, return error status and halt bootstrap process
- **Distribution Detection Failure**: If distribution cannot be detected, log error and exit with failure status

### Idempotency Error Handling
- **Package Check Failures**: If package existence checks fail, assume package is not installed and attempt installation
- **Permission Errors**: If package installation fails due to permissions, log error and exit (bootstrap requires root privileges)

### Logging Strategy
- **Success Cases**: Log when packages are already installed vs newly installed
- **Failure Cases**: Log specific error messages with package names and distribution context
- **Progress Tracking**: Log start and completion of each major installation phase

## Testing Strategy

### Dual Testing Approach
The testing strategy combines unit tests for specific scenarios with property-based tests for comprehensive coverage:

**Unit Tests**:
- Test specific distribution detection scenarios (Amazon Linux 2023, Ubuntu 22.04, etc.)
- Test error conditions (missing package manager, permission failures)
- Test edge cases (empty package lists, malformed distribution detection)
- Test integration between functions

**Property-Based Tests**:
- Test universal properties across all supported distributions
- Test idempotency across multiple execution runs
- Test package installation behavior with randomized package states
- Minimum 100 iterations per property test to ensure comprehensive coverage

### Property-Based Testing Configuration
Using **Bash Unit Testing Framework** with property-based testing extensions:
- Each property test runs minimum 100 iterations
- Tests tagged with: **Feature: ec2-bootstrap-refactor, Property {number}: {property_text}**
- Property tests focus on universal behaviors that should hold across all inputs
- Unit tests focus on specific examples and integration points

### Test Environment Setup
- **Mock Package Managers**: Create mock rpm, yum, dpkg, apt-get commands for testing
- **Distribution Simulation**: Mock /etc/os-release and other distribution detection files
- **Package State Simulation**: Mock package installation states for idempotency testing
- **Logging Verification**: Capture and verify log output for different scenarios

## Implementation Notes

### Key Design Decisions

1. **Preserve Existing Function Names**: The main `install_packages()` function keeps its name to maintain compatibility with the existing SSM document structure.

2. **Backward Compatibility**: All existing specialized installation functions (`install_java`, `install_cloudwatch_*`, `install_awscli`) remain unchanged to minimize risk.

3. **Gradual Refactoring**: Only the general package installation logic is refactored, leaving other bootstrap functionality untouched.

4. **Enhanced RPM Idempotency**: RPM-based systems will gain the same individual package checking that Debian systems currently have.

### Migration Strategy

1. **Phase 1**: Create new `install_system_packages()` function with unified logic
2. **Phase 2**: Create `is_package_installed()` helper function for both distributions  
3. **Phase 3**: Refactor `install_packages()` to use new unified function
4. **Phase 4**: Remove duplicated package installation code
5. **Phase 5**: Add comprehensive testing and validation

### Risk Mitigation

- **Extensive Testing**: Property-based tests ensure behavior works across all supported distributions
- **Gradual Rollout**: Changes can be deployed incrementally with rollback capability
- **Logging Enhancement**: Improved logging helps diagnose any issues in production
- **Backward Compatibility**: Existing SSM document structure remains unchanged