# PropPal 🏡

**AI-Powered Multi-Agent Real Estate Platform for Pakistan**

PropPal is an intelligent real estate platform that simplifies property search, listing, and builder service discovery through conversational AI agents. Built with a modern multi-agent architecture, it uses LangGraph to orchestrate specialized agents for property discovery and builder recommendations.

## 🛠️ Technology Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Clerk (Auth)
- **Backend**: FastAPI (Python 3.12), LangGraph (Multi-Agent System), Groq (Llama 3.1)
- **Databases**: PostgreSQL 17 (Relational), Qdrant (Vector / Semantic Search)
- **Infrastructure**: Docker Compose, Turborepo

## 🚀 How to Run

### 1. Prerequisites

- Docker & Docker Compose
- Node.js 18+
- Python 3.12+

### 2. Infrastructure Setup

Start the local database and vector store:

```bash
docker-compose up -d
```

### 3. Environment Configuration

Create a `.env` file in the root directory and `apps/backend/.env` with the following configuration:

```env
# Databases
DATABASE_URL=postgresql://user:password@localhost:5432/proppal
QDRANT_URL=http://localhost:6333

# AI / LLM
GROQ_API_KEY=your_groq_api_key

# Frontend / Auth
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Install Dependencies

You can use the root setup script or manual commands:

```bash
# Using root script
npm run setup

# OR manual installation
npm install
cd apps/backend
pip install -r requirements.txt
```

### 5. Data Synchronization (Optional)

To populate your local environment with sample data and generate embeddings, run the super backfill script:

```bash
# From apps/backend
python jobs/super_backfill.py
```

### 6. Launch the Application

Run both frontend and backend using Turbo:

```bash
# Start both frontend and backend
npm run dev

# Start only the backend from root
npm run dev:backend
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

Built with ❤️ by the PropPal Team.
🏠 *Making Real Estate Smarter with AI* ✨
