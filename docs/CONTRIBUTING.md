# Contributing to PropPal

Thank you for your interest in contributing to PropPal! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PropPal.git
   cd PropPal
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/bilalrana8718/PropPal.git
   ```
4. **Install dependencies**:
   ```bash
   npm install
   cd apps/backend && pip install -r requirements.txt && cd ../..
   ```
5. **Create a new branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Process

### 1. Sync with Upstream

Before starting work, ensure your fork is up to date:

```bash
git checkout main
git pull upstream main
git push origin main
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 3. Make Your Changes

- Write clean, readable code
- Follow the project's coding standards
- Add tests for new features
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run linters
npm run lint

# Format code
npm run format

# Run tests
npm run test

# Test in Docker
npm run docker:up
```

### 5. Commit Your Changes

Follow our [commit guidelines](#commit-guidelines).

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Create a Pull Request

- Go to your fork on GitHub
- Click "New Pull Request"
- Select your feature branch
- Fill out the PR template
- Submit the pull request

## Coding Standards

### TypeScript/JavaScript

- **Style Guide**: We use Prettier for code formatting
- **Linting**: ESLint with TypeScript support
- **Naming Conventions**:
  - Use `camelCase` for variables and functions
  - Use `PascalCase` for components and classes
  - Use `UPPER_CASE` for constants
  - Use descriptive names

Example:

```typescript
// Good
const fetchUserData = async (userId: string) => { ... }
const MAX_RETRY_ATTEMPTS = 3
const UserProfile: React.FC<Props> = ({ user }) => { ... }

// Bad
const x = async (id) => { ... }
const retry = 3
const profile = ({ u }) => { ... }
```

### Python

- **Style Guide**: PEP 8 with Black formatting
- **Line Length**: 120 characters
- **Naming Conventions**:
  - Use `snake_case` for functions and variables
  - Use `PascalCase` for classes
  - Use `UPPER_CASE` for constants

Example:

```python
# Good
def fetch_user_data(user_id: str) -> dict:
    ...

class UserService:
    MAX_RETRY_ATTEMPTS = 3

# Bad
def FetchUserData(UserId):
    ...
```

### File Organization

#### TypeScript/React

```
component-name/
├── index.tsx              # Main component
├── component-name.test.tsx # Tests
└── types.ts               # Type definitions (if needed)
```

#### Python

```
module_name/
├── __init__.py
├── service.py
└── tests/
    └── test_service.py
```

### Import Order

#### TypeScript

```typescript
// 1. External dependencies
import React from 'react'
import { useRouter } from 'next/router'

// 2. Internal packages
import { Button } from '@proppal/ui'
import { formatCurrency } from '@proppal/utils'

// 3. Relative imports
import { UserProfile } from './user-profile'
import type { User } from './types'
```

#### Python

```python
# 1. Standard library
import os
from typing import Dict, List

# 2. Third-party packages
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local imports
from common.utils import format_response
from services.user import UserService
```

## Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no code change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```bash
feat(web): add property search functionality

Implement search component with filters for property type,
location, and price range.

Closes #123

---

fix(backend): resolve MongoDB connection timeout

Update connection string to include retry settings.

Fixes #456

---

docs: update development setup instructions

Add Docker setup instructions and troubleshooting guide.
```

### Scope

The scope should indicate the area of the codebase:
- `web`: Next.js web app
- `backend`: FastAPI backend
- `ui`: UI component package
- `schemas`: Schemas package
- `utils`: Utils package
- `docker`: Docker configuration
- `ci`: CI/CD pipelines

## Pull Request Process

### PR Checklist

Before submitting a PR, ensure:

- [ ] Code follows the project's coding standards
- [ ] All tests pass (`npm run test`)
- [ ] Linting passes (`npm run lint`)
- [ ] Code is formatted (`npm run format`)
- [ ] Documentation is updated
- [ ] Commit messages follow the guidelines
- [ ] PR description clearly explains the changes
- [ ] Related issues are referenced

### PR Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123

## Testing
Describe how you tested the changes

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests
- [ ] All tests pass
- [ ] Documentation is updated
```

### Review Process

1. **Automated Checks**: CI/CD will run tests and linting
2. **Code Review**: At least one maintainer must review
3. **Address Feedback**: Make requested changes
4. **Approval**: Once approved, a maintainer will merge

## Project Structure

Understanding the monorepo structure:

```
PropPal/
├── apps/               # Applications
│   ├── backend/       # FastAPI backend
│   └── web/           # Next.js frontend
├── packages/          # Shared packages
│   ├── config/       # Shared configs
│   ├── schemas/      # TypeScript schemas
│   ├── ui/           # React components
│   └── utils/        # Utility functions
├── infra/            # Infrastructure
│   └── docker/       # Docker configs
└── scripts/          # Build scripts
```

### When to Create a New Package

Create a new package in `packages/` when:
- Code is shared across multiple apps
- The code is a self-contained unit
- It has clear boundaries and responsibilities

### When to Modify an App

Modify code in `apps/` when:
- It's specific to that application
- It doesn't need to be shared
- It's tightly coupled to the app's logic

## Questions?

If you have questions:
1. Check the [Development Guide](./DEVELOPMENT.md)
2. Search existing [GitHub Issues](https://github.com/bilalrana8718/PropPal/issues)
3. Create a new issue with the `question` label

Thank you for contributing to PropPal! 🏠✨

