# PropPal 🏡

**AI-Powered Multi-Agent Real Estate Platform for Pakistan**

[![Phase 0](https://img.shields.io/badge/Phase%200-Complete-success)](./PHASE0_COMPLETE.md)
[![License](https://img.shields.io/badge/License-ISC-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Development Guide](#-development-guide)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Team](#-team)
- [License](#-license)

---

## 🎯 Overview

PropPal is an **intelligent real estate platform** designed specifically for Pakistan's property market. It leverages cutting-edge AI technologies to revolutionize how buyers, sellers, and builders interact with real estate.

### Vision

To create Pakistan's most intelligent real estate platform that makes property search, listing, and service discovery as simple as having a conversation.

### Core Capabilities

- **🤖 Conversational AI**: Natural language property search powered by LLMs
- **🔍 Semantic Search**: Vector-based similarity search using Qdrant
- **🏗️ Multi-Agent System**: Specialized AI agents for different tasks
- **🎯 Smart Filtering**: Intelligent filter extraction from natural language
- **📍 Location Intelligence**: Geo-based search and ranking
- **🔄 Real-time Sync**: WebSocket-based chat and updates

---

## ✨ Key Features

### For Buyers
- **Natural Language Search**: "Find me a 3-bedroom apartment in Islamabad under 1 crore"
- **Voice Input**: Speak your requirements naturally
- **Smart Recommendations**: AI-powered property suggestions
- **Interactive Chat**: Real-time conversation with AI agents
- **Property Cards**: Visual property browsing with images and details
- **Saved Sessions**: Resume your searches anytime

### For Sellers
- **AI-Assisted Listings**: Interactive form with voice input
- **Smart Property Creation**: AI extracts details from natural language
- **Listing Management**: View, edit, and delete your properties
- **Dashboard**: Track your listings and inquiries

### For Builders
- **Profile Management**: Showcase your company and expertise
- **Service Listings**: Advertise construction and renovation services
- **Search Visibility**: Get discovered through AI-powered search
- **Category-based Organization**: Services organized by type

### AI Agents

1. **Router Agent**: Intelligent query classification and routing
2. **Listing Agent**: Property search and creation
3. **Builder Agent**: Builder profiles and services search
4. **Booking Agent**: (Coming soon) Visit scheduling

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
├─────────────────────────────────────────────────────────────┤
│  Next.js Web App (Port 3000)                                │
│  - React 19 + TypeScript                                    │
│  - Tailwind CSS + Framer Motion                             │
│  - Clerk Authentication                                      │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/WebSocket
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway Layer                        │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend (Port 8000)                                │
│  - REST APIs + WebSocket                                    │
│  - Request validation (Pydantic)                            │
│  - CORS middleware                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  Router    │ │  Listing   │ │  Builder   │
│  Agent     │ │  Agent     │ │  Agent     │
│            │ │            │ │            │
│ LangGraph  │ │ LangGraph  │ │ LangGraph  │
│ + Groq LLM │ │ + Tools    │ │ + Tools    │
└────────────┘ └────────────┘ └────────────┘
         │           │           │
         └───────────┼───────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
├─────────────────────────────────────────────────────────────┤
│  MongoDB Atlas                    Qdrant Vector DB          │
│  - User data                      - Property embeddings     │
│  - Properties                     - Builder embeddings      │
│  - Builder profiles               - Service embeddings      │
│  - Services                       - Semantic search         │
│  - Chat history                                             │
└─────────────────────────────────────────────────────────────┘
```

### Agent Architecture

```
User Query → Router Agent (Classification)
                    ↓
         ┌──────────┼──────────┐
         ▼          ▼          ▼
   Listing      Builder    General
   Agent        Agent       Chat
      ↓            ↓
   Search       Search
   Tool         Tool
      ↓            ↓
   Qdrant      Qdrant
   Vector      Vector
   Search      Search
      ↓            ↓
   MongoDB     MongoDB
   Fetch       Fetch
      ↓            ↓
   Results     Results
```

### Data Flow: Property Search

1. **User Input**: "I want a modern apartment in Islamabad"
2. **Classification**: Router Agent → `listing_agent`
3. **Filter Extraction**: LLM extracts filters (`city: Islamabad`, `property_type: apartment`)
4. **MongoDB Filtering**: Filter properties matching criteria
5. **Qdrant Retrieval**: Fetch embeddings for filtered properties
6. **Similarity Calculation**: Compute cosine similarity with query embedding
7. **Ranking**: Sort by relevance score
8. **Response**: Return top 10 properties with details

---

## 🛠️ Technology Stack

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 15.5.4 | React framework with SSR |
| **React** | 19 | UI library |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **Framer Motion** | 11.x | Animations |
| **Clerk** | 6.x | Authentication |

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.12+ | Backend language |
| **FastAPI** | 0.115+ | API framework |
| **LangChain** | Latest | LLM orchestration |
| **LangGraph** | Latest | Agent workflows |
| **Groq** | Latest | LLM inference (Llama 3.1) |
| **Motor** | Latest | Async MongoDB driver |

### Databases
| Technology | Purpose |
|-----------|---------|
| **MongoDB Atlas** | Primary database (documents) |
| **Qdrant** | Vector similarity search |

### AI/ML
| Technology | Purpose |
|-----------|---------|
| **Sentence Transformers** | Text embeddings (384-dim) |
| **Groq LLaMA 3.1** | Chat completion & structured output |
| **LangChain Tools** | Function calling |

### DevOps
| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerization |
| **Turborepo** | Monorepo management |
| **Git** | Version control |

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.12+ ([Download](https://www.python.org/))
- **MongoDB Atlas** account ([Sign up](https://www.mongodb.com/cloud/atlas))
- **Qdrant** instance (local or cloud) ([Docs](https://qdrant.tech/))
- **Groq API Key** ([Get one](https://console.groq.com/))
- **Clerk** account ([Sign up](https://clerk.com/))

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/bilalrana8718/PropPal.git
cd PropPal
```

#### 2. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
cd apps/backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.runtime.txt
cd ../..
```

#### 3. Environment Configuration

Create `.env` files in the root and configure:

**Root `.env`:**
```env
# MongoDB
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/proppal?retryWrites=true&w=majority
MONGODB_DB_NAME=proppal

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key  # Optional

# Groq
GROQ_API_KEY=your_groq_api_key

# Clerk (for frontend)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# API URLs
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Backend `.env` (`apps/backend/.env`):**
```env
MONGODB_URL=mongodb+srv://user:password@cluster.mongodb.net/proppal
MONGODB_DB_NAME=proppal
GROQ_API_KEY=your_groq_api_key
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key
```

#### 4. Initialize Qdrant Collections

```bash
cd apps/backend
python -m jobs.init_qdrant_collections
```

#### 5. (Optional) Import Sample Data

```bash
# Import properties from JSON
python -m jobs.property_import --json-path ../../data/zameen_listing_results.json --seller-id YOUR_SELLER_ID

# Generate embeddings
python -m jobs.backfill_property_embeddings --batch-size 50
```

#### 6. Start Development Servers

**Terminal 1 - Backend:**
```bash
cd apps/backend
venv\Scripts\activate  # or source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd apps/web
npm run dev
```

**Terminal 3 - Qdrant (if running locally):**
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## 📂 Project Structure

```
PropPal/
├── apps/
│   ├── backend/                    # FastAPI backend
│   │   ├── agents/                # AI agents
│   │   │   ├── router_agent.py   # Main router
│   │   │   ├── listing/          # Listing agent
│   │   │   │   ├── agent.py
│   │   │   │   └── tools/
│   │   │   │       ├── property_search.py
│   │   │   │       ├── property_creation.py
│   │   │   │       └── filter_extractor.py
│   │   │   └── builder/          # Builder agent
│   │   │       ├── agent.py
│   │   │       └── tools/
│   │   │           ├── builder_search.py
│   │   │           └── builder_creation.py
│   │   ├── api/                  # API routes
│   │   │   ├── chat/            # Chat endpoints
│   │   │   ├── properties/      # Property endpoints
│   │   │   ├── builder/         # Builder endpoints
│   │   │   └── users/           # User endpoints
│   │   ├── common/              # Shared utilities
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   └── qdrant.py
│   │   ├── services/            # Business logic
│   │   │   ├── embeddings/      # Embedding generation
│   │   │   └── vector_search/   # Qdrant operations
│   │   ├── models/              # Pydantic models
│   │   ├── jobs/                # Background jobs
│   │   └── main.py              # FastAPI app
│   └── web/                      # Next.js frontend
│       ├── src/
│       │   ├── app/             # App router pages
│       │   │   ├── (landing)/   # Landing page
│       │   │   ├── buyer/       # Buyer dashboard
│       │   │   ├── seller/      # Seller dashboard
│       │   │   ├── builder/     # Builder dashboard
│       │   │   ├── chat/        # Chat interface
│       │   │   └── properties/  # Property details
│       │   ├── components/      # React components
│       │   ├── context/         # React context
│       │   ├── lib/            # Utilities
│       │   └── styles/         # Global styles
│       └── public/             # Static assets
├── data/                        # Sample data
├── docs/                        # Documentation
├── infra/                       # Infrastructure
└── scripts/                     # Automation scripts
```

---

## 💻 Development Guide

### Running Tests

```bash
# Backend tests
cd apps/backend
pytest

# Frontend tests
cd apps/web
npm test
```

### Code Quality

```bash
# Lint all code
npm run lint

# Format all code
npm run format

# Type check
npm run type-check
```

### Database Operations

**Create Qdrant Collections:**
```bash
python -m jobs.init_qdrant_collections
```

**Backfill Embeddings:**
```bash
# Properties
python -m jobs.backfill_property_embeddings --batch-size 100

# Builder profiles
python -m jobs.backfill_builders_profiles_embeddings

# Services
python -m jobs.backfill_builder_services
```

**Migrate to Qdrant:**
```bash
# Migrate all collections
python -m jobs.migrate_to_qdrant

# Migrate specific collection
python -m jobs.migrate_to_qdrant --collection properties
```

### Adding a New Agent

1. Create agent directory: `apps/backend/agents/your_agent/`
2. Implement `agent.py` with LangGraph workflow
3. Create tools in `tools/` directory
4. Register in router: `apps/backend/agents/router_agent.py`
5. Add API routes: `apps/backend/api/your_agent/`

### Adding a New Tool

1. Create tool file: `apps/backend/agents/your_agent/tools/your_tool.py`
2. Use `@tool` decorator from LangChain
3. Define clear docstring (used by LLM)
4. Return JSON-serializable dict
5. Handle errors gracefully

---

## 📚 API Documentation

### REST Endpoints

#### Authentication
- `POST /api/users/sync` - Sync Clerk user to MongoDB
- `GET /api/users/me` - Get current user

#### Properties
- `GET /api/properties` - List properties
- `GET /api/properties/{id}` - Get property details
- `POST /api/properties` - Create property
- `DELETE /api/properties/{id}` - Delete property

#### Search
- `POST /api/search/properties` - Vector search properties
- `POST /api/search/builders` - Search builder profiles
- `POST /api/search/services` - Search builder services

#### Chat
- `POST /api/chat/message` - Send chat message
- `GET /api/chat/sessions` - List chat sessions
- `GET /api/chat/history` - Get chat history
- `DELETE /api/chat/sessions/{id}` - Delete chat session

#### WebSocket
- `WS /api/chat/ws` - Real-time chat

### WebSocket Protocol

**Connect:**
```
ws://localhost:8000/api/chat/ws?clerk_id=user_123&session_id=session_456
```

**Send Message:**
```json
{
  "type": "message",
  "text": "Find me apartments in Islamabad",
  "clerk_id": "user_123",
  "session_id": "session_456"
}
```

**Receive Response:**
```json
{
  "type": "agent",
  "message": "Found 10 properties matching your search.",
  "classification": "listing_agent",
  "success": true,
  "properties": [...],
  "metadata": {...}
}
```

---

## 🚀 Deployment

### Backend Deployment (Docker)

```bash
# Build image
docker build -t proppal-backend -f apps/backend/Dockerfile .

# Run container
docker run -p 8000:8000 --env-file .env proppal-backend
```

### Frontend Deployment (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd apps/web
vercel --prod
```

### Environment Variables

Ensure all environment variables are set in your deployment platform:
- MongoDB connection string
- Qdrant URL and API key
- Groq API key
- Clerk keys
- API URLs

---

## 🧪 Testing

### Backend Testing

```bash
cd apps/backend
pytest tests/ -v
```

### Frontend Testing

```bash
cd apps/web
npm test
npm run test:e2e
```

### Manual Testing

1. **Property Search**: Chat "Find apartments in Islamabad"
2. **Voice Input**: Use mic button on create listing page
3. **Builder Search**: Chat "I need plumbing services"
4. **Chat History**: Check sidebar for previous sessions

---

## 🔧 Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```
pymongo.errors.ServerSelectionTimeoutError
```
**Solution**: Check your `MONGODB_URL` in `.env` and ensure IP is whitelisted in MongoDB Atlas.

#### 2. Qdrant Not Running
```
requests.exceptions.ConnectionError
```
**Solution**: Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`

#### 3. Groq API Rate Limit
```
Error code: 429 - Rate limit exceeded
```
**Solution**: Wait or upgrade your Groq plan. Consider adding retry logic.

#### 4. Hydration Mismatch (Frontend)
```
Hydration failed because the server rendered HTML didn't match
```
**Solution**: Ensure no conditional rendering based on client-only values (`window`, `Date.now()`). Use `mounted` state if needed.

#### 5. ObjectId Serialization Error
```
PydanticSerializationError: Unable to serialize unknown type: ObjectId
```
**Solution**: Convert all ObjectIds to strings before returning from API/tools.

#### 6. Embedding Generation Slow
**Solution**: Reduce batch size, use GPU if available, or cache embeddings.

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Contribution Guidelines

1. **Fork** the repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit** with conventional commits
   ```bash
   git commit -m "feat: add amazing feature"
   ```
4. **Push** to your fork
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open** a Pull Request

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Test changes
- `chore:` Build/tooling changes

### Code Style

- **Python**: PEP 8, use `black` for formatting
- **TypeScript**: ESLint + Prettier
- **Naming**: Use descriptive names
- **Comments**: Explain why, not what

---

## 🧑‍🤝‍🧑 Team

**PropPal FYP Team (2025-2026)**

| Name | Roll Number | Responsibilities |
|------|------------|------------------|
| **Muhammad Bilal** | 22I-0806 | Chat UI, Router Agent, Booking Agent |
| **Rana Bilal Akbar** | 22I-1094 | Listing Agent, APIs, Optimizations |
| **Mehboob Ali Shah** | 22I-1208 | Builder Agent, Geo Ranking |

**Supervisor**: Dr. Akhtar Jamil (FAST-NUCES, Islamabad)

---

## 🛤️ Roadmap

### ✅ Phase 0 (Complete)
- [x] Monorepo setup with Turborepo
- [x] Docker environment
- [x] MongoDB Atlas integration
- [x] Shared schemas package

### ✅ Phase 1 (Complete - Jan 2025)
- [x] Router Agent with LangGraph
- [x] Listing Agent (search + creation)
- [x] Builder Agent (profiles + services)
- [x] Chat UI with WebSocket
- [x] Qdrant vector search
- [x] Filter extraction from natural language

### 🔄 Phase 2 (In Progress - Feb-Mar 2025)
- [ ] Booking Agent MVP
- [ ] Enhanced property details
- [ ] Builder bidding system
- [ ] Advanced filtering
- [ ] Performance optimization

### 🔮 Phase 3 (Apr-May 2025)
- [ ] Geo-ranking system
- [ ] Schools/Hospitals APIs
- [ ] Map integration
- [ ] Mobile app (React Native)
- [ ] Multilingual support (Urdu)

### 🚀 Phase 4 (Jun-Jul 2025)
- [ ] RAG optimization
- [ ] Multi-agent collaboration
- [ ] Production deployment
- [ ] Analytics dashboard

---

## 📝 License

ISC License - see [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FAST-NUCES Islamabad** for academic support
- **Dr. Akhtar Jamil** for supervision and guidance
- **LangChain** team for the amazing framework
- **Groq** for fast LLM inference
- **Qdrant** for vector search capabilities
- All contributors and testers

---

## 📬 Contact & Support

- **GitHub**: [bilalrana8718/PropPal](https://github.com/bilalrana8718/PropPal)
- **Issues**: [Report bugs or request features](https://github.com/bilalrana8718/PropPal/issues)
- **Discussions**: [Join the conversation](https://github.com/bilalrana8718/PropPal/discussions)

---

## 📊 Project Stats

- **Lines of Code**: 50,000+
- **AI Agents**: 3 (Router, Listing, Builder)
- **API Endpoints**: 20+
- **Database Collections**: 6
- **Vector Dimensions**: 384

---

<div align="center">

**Built with ❤️ by the PropPal Team**

**🏠 Making Real Estate Smarter with AI ✨**

[Quick Start](./docs/QUICK_START.md) • [API Docs](http://localhost:8000/docs) • [Contributing](./docs/CONTRIBUTING.md)

⭐ **Star us on GitHub if you find this project useful!** ⭐

</div>
