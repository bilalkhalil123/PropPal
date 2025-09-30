PropPal/
├── apps/
│   ├── web/                  # Next.js app (buyer/seller/builder portals)
│   │   ├── public/            # Static assets
│   │   ├── src/
│   │   │   ├── components/    # Web-specific UI components
│   │   │   ├── pages/         # Next.js pages (SSR, routing)
│   │   │   ├── hooks/         # React hooks
│   │   │   ├── lib/           # API client wrappers, utils
│   │   │   └── styles/        # TailwindCSS, global styles
│   │   ├── next.config.js
│   │   └── package.json
│   │
│   ├── mobile/               # React Native app
│   │   ├── android/
│   │   ├── ios/
│   │   ├── src/
│   │   │   ├── components/    # Mobile-specific UI components
│   │   │   ├── screens/       # Navigation screens
│   │   │   ├── hooks/         # RN hooks (auth, data fetching)
│   │   │   ├── lib/           # API clients, SSE/WebSocket handlers
│   │   │   └── assets/        # Images, fonts
│   │   ├── app.json
│   │   └── package.json
│   │
│   └── backend/              # FastAPI backend (microservices)
│       ├── services/
│       │   ├── gateway/       # API gateway / router agent
│       │   │   ├── main.py
│       │   │   ├── routers/
│       │   │   ├── models/
│       │   │   └── schemas/
│       │   ├── listing/       # Listing agent service
│       │   ├── builder/       # Builder agent service
│       │   ├── booking/       # Booking agent service
│       │   └── nlp/           # NLP/RAG/LLM service
│       ├── common/            # Shared backend utils (logging, config, DB)
│       ├── tests/             # Backend unit/integration tests
│       ├── Dockerfile
│       └── pyproject.toml     # Poetry or Pipenv
│
├── packages/                  # Shared libraries (used by web, mobile, backend)
│   ├── ui/                    # Cross-platform React components (if reusable)
│   ├── schemas/               # Shared API contracts (OpenAPI/TypeScript types)
│   ├── utils/                 # Common utilities (validation, constants, helpers)
│   └── config/                # Env configs, secrets management wrappers
│
├── infra/                     # Infra-as-code (deployment)
│   ├── docker/                # Docker compose files for local dev
│   ├── k8s/                   # Kubernetes manifests (if scaling)
│   └── terraform/             # Infra provisioning (optional)
│
├── tests/                     # End-to-end tests (Playwright, Detox, Postman collections)
│
├── scripts/                   # Dev scripts (lint, format, DB migrations, setup)
│
├── .github/workflows/         # CI/CD pipelines
├── package.json               # Root workspace config (for web + mobile deps)
├── pyproject.toml              # Root Python config (backend deps mgmt)
├── README.md
└── turbo.json / nx.json        # Monorepo task runner config (Turborepo or Nx)
