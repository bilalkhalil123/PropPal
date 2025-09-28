# PropPal 🏡

*A Multi-Agent AI-Powered Real Estate Platform*

---

## 📌 Overview

PropPal is an **AI-driven, multi-agent real estate platform** designed to revolutionize property search, listing, and engagement in Pakistan’s real estate sector. Unlike existing portals that rely on rigid filters and manual inputs, PropPal leverages **Natural Language Processing (NLP)**, **Retrieval-Augmented Generation (RAG)**, and **intelligent automation** to connect buyers, sellers, and builders seamlessly.

---

## 🚀 Key Features

* **Conversational Property Search** – Buyers can search using natural language queries (e.g., *“3-bedroom apartment near a school and hospital in G-10/3”*).
* **AI-Assisted Property Listings** – Sellers can create listings via natural language or assisted forms.
* **Builder Integration** – Builders showcase expertise, pitch proposals, and bid on projects.
* **AI Visit Booking Agent** – Automated scheduling, rescheduling, and reminders for property visits.
* **Nearby Amenities Detection** – Schools, hospitals, commute insights via geo-intelligence.
* **Multilingual Support** – English and Urdu for accessibility across diverse user groups.

---

## 🛠️ Technology Stack

* **Frontend**: React.js (Web), React Native (Mobile)
* **Backend**: Node.js, Express.js, MongoDB (MERN stack)
* **AI & NLP**:

  * LangChain / LangGraph for multi-agent workflows
  * LLaMA 3 (local) + OpenAI GPT for semantic search & chat
  * Whisper for voice-to-text input (English/Urdu)
* **Geo Intelligence**: Google Maps API (geocoding, commute time, amenities detection)
* **Vector Search**: MongoDB Vector Search for semantic retrieval (RAG)
* **Security & Auth**: Role-Based Access Control (RBAC), modern auth libraries
* **Notifications**: Email, SMS, push notifications

---

## 📂 System Modules

1. **Client Web App** (Buyer, Seller, Builder dashboards)
2. **Client Mobile App** (voice/text search, quick listing, notifications)
3. **Backend Services & API Gateway** (auth, business logic, APIs)
4. **NLP & RAG Module** (semantic search, multilingual support)
5. **Search & Amenities Engine** (geo-coding, amenities ranking, maps)
6. **AI Visit Booking Agent** (autonomous scheduling & reminders)

---

## 👥 Stakeholders

* **Buyers** – Search & shortlist properties via conversational queries.
* **Sellers** – List properties easily with AI-assisted forms.
* **Builders/Developers** – Showcase expertise, pitch projects, bid proposals.
* **Admins** – Manage system operations, transparency, and platform quality.
* **Agents** – Use PropPal as an additional channel to reach clients.

---

## 📅 Project Timeline (FYP Milestones)

* **Iteration 1 (Sept–Oct 2025)**: Listing Agent, Builder Agent MVP, Chat UI + Router Agent.
* **Iteration 2 (Nov–Dec 2025)**: Listing Agent v2, Builder Agent v2, Booking Agent MVP.
* **Iteration 3 (Feb–Mar 2026)**: APIs (schools, hospitals, commute), Geo-ranking, UI integration.
* **Iteration 4 (Apr–May 2026)**: Optimizations (RAG, multi-agent workflows, multi-response Chat UI).

---

## 🧑‍🤝‍🧑 Team Members

* **Muhammad Bilal (22I-0806)** – Chat UI + Router Agent + Booking Agent + UI Integration.
* **Rana Bilal Akbar (22I-1094)** – Listing Agent + APIs (Schools/Hospitals) + Optimizations.
* **Mehboob Ali Shah (22I-1208)** – Builder Agent + Geo Ranking + Multi-Agent Optimization.
* **Supervisor**: Dr. Akhtar Jamil (FAST-NUCES, Islamabad).

---

## 📖 Contribution Guidelines

1. **Branching Model**

   * `main` → Stable production code
   * `dev` → Active development
   * `feature/*` → One branch per feature/module

2. **Commit Messages** (Conventional Commits)

   ```
   feat(listing-agent): add semantic search filter
   fix(builder-agent): resolve bidding bug
   docs(readme): update team roles
   ```

3. **Pull Requests**

   * All changes must go through PRs.
   * At least **1 reviewer approval** required.

---

## ⚙️ Development Setup

```bash
# Clone repo
git clone https://github.com/<your-org>/PropPal.git
cd PropPal

# Backend setup
cd backend
npm install
npm run dev

# Frontend setup
cd ../frontend
npm install
npm start
```

---
