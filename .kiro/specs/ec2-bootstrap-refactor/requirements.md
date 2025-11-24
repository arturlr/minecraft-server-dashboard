# Requirements Document

## Introduction

The EC2 bootstrap SSM document in `cfn/templates/ec2.yaml` contains duplicated package installation logic across multiple functions. Specifically, the `install_minecraft_deb()` function and `install_required_packages()` function both handle installation of common packages (jq, zip, unzip, wget, screen, net-tools) for Debian-based systems. This duplication makes the code harder to maintain and increases the risk of inconsistencies.

This feature aims to refactor the bootstrap script to use a single, unified list of packages that need to be installed, eliminating duplication and improving maintainability.

## Glossary

- **SSM Document**: AWS Systems Manager document that defines commands to run on EC2 instances
- **Bootstrap Script**: Shell script that runs when an EC2 instance first starts to install required software
- **Package Manager**: System tool for installing software (yum for RPM-based, apt-get for Debian-based)
- **CloudFormation Template**: Infrastructure-as-code file defining AWS resources

## Requirements

### Requirement 1

**User Story:** As a DevOps engineer, I want a single source of truth for package dependencies, so that I can easily maintain and update the list of required packages without risking inconsistencies.

#### Acceptance Criteria

1. WHEN the bootstrap script installs packages THEN the system SHALL use a single unified list of required packages
2. WHEN a package is already installed THEN the system SHALL skip reinstalling that package
3. WHEN installing packages on Debian-based systems THEN the system SHALL check each package individually before attempting installation
4. WHEN installing packages on RPM-based systems THEN the system SHALL use the appropriate package manager commands

### Requirement 2

**User Story:** As a system administrator, I want the bootstrap script to be idempotent, so that running it multiple times produces the same result without errors.

#### Acceptance Criteria

1. WHEN the bootstrap script runs multiple times THEN the system SHALL not fail if packages are already installed
2. WHEN checking for installed packages THEN the system SHALL use distribution-appropriate commands
3. WHEN all required packages are already installed THEN the system SHALL log this status and continue without errors

### Requirement 3

**User Story:** As a developer, I want clear separation of concerns in the bootstrap script, so that each function has a single, well-defined responsibility.

#### Acceptance Criteria

1. WHEN the bootstrap script defines package installation functions THEN each function SHALL handle only one specific task
2. WHEN installing Java THEN the system SHALL use a dedicated function separate from general package installation
3. WHEN installing CloudWatch agent THEN the system SHALL use a dedicated function separate from general package installation
4. WHEN installing general utility packages THEN the system SHALL use a dedicated function that works for both RPM and Debian-based systems
