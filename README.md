# PropPal 🏡

*A Multi-Agent AI-Powered Real Estate Platform*

[![Phase 0](https://img.shields.io/badge/Phase%200-Complete-success)](./PHASE0_COMPLETE.md)
[![License](https://img.shields.io/badge/License-ISC-blue.svg)](./LICENSE)

---

## 🚀 Quick Start

Get started in 5 minutes:

```bash
# 1. Clone and install
git clone https://github.com/bilalrana8718/PropPal.git
cd PropPal
npm install

# 2. Setup Python
cd apps/backend
python -m venv venv
venv\Scripts\activate  # Windows (or: source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
cd ../..

# 3. Configure MongoDB Atlas
cp .env.example .env
# Edit .env with your MongoDB Atlas connection string

# 4. Start backend services
npm run docker:up
```

**Access:** http://localhost:8000 (Gateway API) | http://localhost:8000/docs (API Docs)

📖 **[Full Quick Start Guide](./docs/QUICK_START.md)**

---

## 📌 Overview

PropPal is an **AI-driven, multi-agent real estate platform** for Pakistan's real estate sector, leveraging:

- 🤖 **NLP & RAG** for conversational property search
- 🏗️ **Multi-Agent System** for intelligent automation
- 🗺️ **Geo-Intelligence** for location-based insights
- 🌐 **Multilingual Support** (English & Urdu)

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Web (Next.js) │ ──────┐
│  (Port 3000)    │       │
└─────────────────┘       │
                          │
┌─────────────────┐       │    ┌──────────────────┐
│ Mobile (RN)     │ ──────┼───▶│  Gateway API     │
│                 │       │    │  (Port 8000)     │
└─────────────────┘       │    └──────────────────┘
                          │              │
                          │              ├──▶ MongoDB Atlas
                          │              │
                          │    ┌──────────────────┐
                          └───▶│  NLP Service     │
                               │  (Port 8001)     │
                               └──────────────────┘
```

---

## 🛠️ Technology Stack

### Frontend
- **Web**: Next.js 15 + React 19 + TypeScript
- **Mobile**: React Native (TBD)
- **Styling**: Tailwind CSS

### Backend
- **API Gateway**: FastAPI + Python 3.13
- **Database**: MongoDB Atlas (external)
- **AI/NLP**: LangChain, LangGraph, OpenAI GPT, LLaMA 3

### Infrastructure
- **Monorepo**: Turborepo
- **Containerization**: Docker Compose
- **Deployment**: Vercel (Web), Docker (Backend)

---

## 📂 Project Structure

```
PropPal/
├── apps/
│   ├── backend/        # FastAPI backend services
│   └── web/            # Next.js web application
├── packages/
│   └── schemas/        # Shared TypeScript schemas
├── infra/
│   └── docker/         # Docker configuration
├── docs/               # Documentation
└── scripts/            # Automation scripts
```

---

## 🎯 Key Features

- ✅ **Conversational Search**: Natural language property queries
- ✅ **AI-Assisted Listings**: Smart form assistance for sellers
- ✅ **Builder Integration**: Proposal bidding & project showcase
- ✅ **Smart Booking**: Automated visit scheduling
- ✅ **Amenities Detection**: Schools, hospitals, commute insights
- ✅ **Multilingual**: English & Urdu support

---

## 📖 Documentation

### Getting Started
- 🚀 **[Quick Start (5 min)](./docs/QUICK_START.md)** - Get running fast
- 📘 **[Phase 0 Setup](./docs/PHASE0_SETUP.md)** - Complete setup guide
- 🐳 **[Docker Guide](./infra/docker/README.md)** - Docker documentation

### Development
- 💻 **[Development Guide](./docs/DEVELOPMENT.md)** - Development workflows
- 🤝 **[Contributing](./docs/CONTRIBUTING.md)** - Contribution guidelines
- 📂 **[Repository Structure](./docs/Repo-Structure.md)** - Code organization

### Reference
- ✅ **[Phase 0 Complete](./PHASE0_COMPLETE.md)** - Implementation summary

---

## 🧑‍🤝‍🧑 Team

**PropPal FYP Team (2025-2026)**

- **Muhammad Bilal** (22I-0806) - Chat UI, Router Agent, Booking Agent
- **Rana Bilal Akbar** (22I-1094) - Listing Agent, APIs, Optimizations
- **Mehboob Ali Shah** (22I-1208) - Builder Agent, Geo Ranking
- **Supervisor**: Dr. Akhtar Jamil (FAST-NUCES, Islamabad)

---

## 🛤️ Development Roadmap

### ✅ Phase 0 (Complete)
- [x] Monorepo setup with Turborepo
- [x] Docker environment (backend services)
- [x] MongoDB Atlas integration
- [x] Shared schemas package
- [x] Linting & formatting

### 🔄 Phase 1 (In Progress - Sept-Oct 2025)
- [ ] Listing Agent MVP
- [ ] Builder Agent MVP
- [ ] Chat UI + Router Agent
- [ ] Basic property search

### 🔮 Phase 2 (Nov-Dec 2025)
- [ ] Listing Agent v2
- [ ] Builder Agent v2
- [ ] Booking Agent MVP
- [ ] Enhanced search

### 🚀 Phase 3 (Feb-Mar 2026)
- [ ] Schools/Hospitals APIs
- [ ] Geo-ranking system
- [ ] UI/UX integration
- [ ] Mobile app

### ⚡ Phase 4 (Apr-May 2026)
- [ ] RAG optimization
- [ ] Multi-agent workflows
- [ ] Performance tuning
- [ ] Production deployment

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./docs/CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'feat: add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

**Commit Convention**: We use [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📝 Available Scripts

```bash
# Backend Services
npm run docker:up      # Start Docker services
npm run docker:down    # Stop Docker services
npm run docker:logs    # View service logs

# Development
npm run dev            # Start all dev servers
npm run build          # Build backend + schemas
npm run lint           # Lint all code
npm run format         # Format all code
npm run test           # Run all tests

# Code Quality
npm run lint:js        # Lint JavaScript/TypeScript
npm run lint:py        # Lint Python
npm run format:js      # Format JS/TS
npm run format:py      # Format Python
```

---

## 📜 License

ISC License - see [LICENSE](./LICENSE) file for details

---

## 🙏 Acknowledgments

- **FAST-NUCES Islamabad** for academic support
- **Dr. Akhtar Jamil** for supervision and guidance
- All contributors and testers

---

## 📬 Contact

- **GitHub**: [bilalrana8718/PropPal](https://github.com/bilalrana8718/PropPal)
- **Issues**: [Report a bug or request a feature](https://github.com/bilalrana8718/PropPal/issues)

---

<div align="center">

**Built with ❤️ by the PropPal Team**

**🏠 Making Real Estate Smarter ✨**

[Documentation](./docs) • [Quick Start](./docs/QUICK_START.md) • [Contributing](./docs/CONTRIBUTING.md)

</div>

