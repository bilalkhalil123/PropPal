# PropPal Frontend Tests

This directory contains all frontend tests for PropPal.

## Structure

```
__tests__/
├── integration/                    # Integration tests
│   └── PropertySearch.test.tsx    # Property search flow
└── README.md
```

```
components/__tests__/               # Component tests
├── PropertyCard.test.tsx          # Property card component
└── ChatMessage.test.tsx           # Chat message component
```

## Running Tests

### All Tests
```bash
npm test
```

### Watch Mode
```bash
npm test -- --watch
```

### With Coverage
```bash
npm test -- --coverage
```

### Specific Test File
```bash
npm test PropertyCard.test.tsx
```

## Requirements

Install test dependencies:
```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom @testing-library/user-event jest jest-environment-jsdom msw
```

## Configuration

- `jest.config.js` - Jest configuration
- `jest.setup.js` - Test setup and mocks

