# PropPal Backend Tests

This directory contains all backend tests for PropPal.

## Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── services/                # Service layer tests
│   └── test_embeddings.py  # Embedding generation tests
├── agents/                  # Agent tests
│   └── listing/
│       ├── test_filter_extractor.py  # Filter extraction tests
│       └── test_property_search.py   # Property search tool tests
├── api/                     # API endpoint tests
│   ├── test_chat.py        # Chat API tests
│   └── test_properties.py  # Properties API tests
├── performance/             # Performance tests
│   ├── locustfile.py       # Load testing scenarios
│   └── test_vector_search.py  # Vector search benchmarks
└── security/                # Security tests
    ├── test_authentication.py  # Auth tests
    └── test_input_validation.py  # Input validation tests
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/services/test_embeddings.py -v
```

### With Coverage
```bash
pytest --cov=. --cov-report=html
```

### Performance Tests
```bash
pytest tests/performance/ -v
```

### Load Tests
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

## Requirements

Install test dependencies:
```bash
pip install -r requirements.test.txt
```

