# Minecraft Server Dashboard Development Guidelines

## Build/Test Commands
- Dashboard Development: `cd dashboard && npm run dev`
- Dashboard Build: `cd dashboard && npm run build`
- Vue Linting: `npm run lint`
- Python Tests: `pytest tests/test_helpers.py`
- Deploy: `sam deploy`

## Code Style
- **Python**: Use type hints, docstrings for functions. Log with standard levels (info/warning/error).
- **Vue**: Use Composition API with `<script setup>`. Organize imports by external/internal.
- **Naming**: camelCase for JS/Vue, snake_case for Python, PascalCase for components.
- **Error Handling**: Always log exceptions. Use try/except blocks with specific error types.
- **State Management**: Use Pinia stores for Vue app state.
- **AWS Integration**: Use helper classes (utilHelper, ec2Helper) for AWS services access.
- **Form Validation**: Define validation rules as local variables in Vue components.
- **Imports**: Group imports by standard library, third-party packages, then local modules.
- **Component Structure**: Keep script, template, style sections organized in Vue files.