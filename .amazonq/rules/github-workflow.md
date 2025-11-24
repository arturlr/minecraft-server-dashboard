# GitHub Issue-to-PR Automation Rules

1. **Branch Naming Conventions**:
   - When a GitHub issue is labeled "q-cli", automatically generate branch name using pattern:
     - Features: `feature/issue-{ISSUE_NUMBER}-{short-description}`
     - Bug fixes: `bugfix/issue-{ISSUE_NUMBER}-{short-description}`
     - Documentation: `docs/issue-{ISSUE_NUMBER}-{short-description}`
     - Hotfixes: `hotfix/issue-{ISSUE_NUMBER}-{short-description}`
     - Refactoring: `refactor/issue-{ISSUE_NUMBER}-{short-description}`

2. **Commit Message Standards**:
   - Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification as defined in `.amazonq/rules/git.md`
   - Always reference the original issue ID (e.g., `fix: Resolve memory leak issue #123`)
   - Include a detailed body explaining the changes when appropriate

3. **Pull Request Process**:
   - PR titles must follow format: `{type}(optional scope): Resolve #{ISSUE_NUMBER}: {ISSUE_TITLE}`
   - PR descriptions must include:
     ```
     - Issue reference: Closes #{ISSUE_NUMBER}
     - Change summary bullet points
     - Automated test results badge
     - Checklist of completed items
   - PR labels: "in review", "needs changes", "ready to merge"

4. **Code Generation Requirements**:
   - All new code must follow project style guide
   - JSDoc comments required for all public functions and classes
   - Include unit tests for new functionality
   - Update documentation for API changes
   - No commented-out code or TODO comments without associated issues

5. **Branch Protection Rules**:
   - Main branch requires pull request reviews before merging
   - Status checks must pass before merging
   - Branch must be up to date before merging
   - No force pushes to protected branches
   - No deletion of protected branches
   - Linear history required (no merge commits)

6. **Issue Templates**:
   - Bug report template:
     ```
     ## Description
     [Clear description of the bug]

     ## Steps to Reproduce
     1. [First step]
     2. [Second step]
     3. [And so on...]

     ## Expected Behavior
     [What you expected to happen]

     ## Actual Behavior
     [What actually happened]

     ## Environment
     - OS: [e.g. Windows 10]
     - Browser: [e.g. Chrome 91]
     - Version: [e.g. 1.2.3]
     ```
   - Feature request template:
     ```
     ## Problem Statement
     [Describe the problem this feature would solve]

     ## Proposed Solution
     [Describe your proposed solution]

     ## Alternatives Considered
     [Any alternative solutions you've considered]

     ## Additional Context
     [Any other context or screenshots]
     ```

7. **Validation Requirements**:
   - Code coverage cannot decrease by more than 2%

