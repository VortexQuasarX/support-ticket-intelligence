# 🛡️ Support Ticket Intelligence AI

> **Enterprise Operations Platform: Hybrid Text-to-SQL & Semantic Search, Multi-Tier Anomaly Engine with AI Diagnostician, and Dual REST API / Streamlit Interfaces.**
> 
> *Developed for the DOTMappers AI Engineer Role Technical Assessment Sprint.*

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [System Architecture](#-system-architecture)
- [Key Engineering Decisions & Rationale](#-key-engineering-decisions--rationale)
- [Multi-Tier Anomaly Detection & AI Diagnostician](#-multi-tier-anomaly-detection--ai-diagnostician)
- [Hybrid Query Engine (Text-to-SQL + Semantic RAG)](#-hybrid-query-engine-text-to-sql--semantic-rag)
- [Quickstart Guide](#-quickstart-guide)
- [One-Click Evaluator Benchmark (`evaluate.py`)](#-one-click-evaluator-benchmark-evaluatepy)
- [Assessment Sample Queries & Verified Outputs](#-assessment-sample-queries--verified-outputs)
- [REST API Specification](#-rest-api-specification)
- [Automated Test Suite (17 Tests)](#-automated-test-suite-17-tests)
- [Production Scaling Roadmap (Walkthrough Discussion)](#-production-scaling-roadmap-walkthrough-discussion)

---

## 🎯 Executive Overview

Modern customer support organizations handle thousands of incoming tickets daily. Operational blindspots—such as silent SLA breaches, extreme resolution outliers, or agent performance drops—directly degrade customer satisfaction (CSAT) and churn.

This system provides a production-grade AI intelligence layer over support operations:
1. **Zero-Overhead Data Ingestion**: Parses, validates, and indexes 500+ raw support tickets into an ACID-compliant, indexed embedded SQLite data engine.
2. **Hybrid Query Engine (Text-to-SQL + Semantic Search)**:
   - **Quantitative**: Converts natural language questions into safe, optimized SQL with closed-loop self-healing error correction.
   - **Qualitative**: Uses vector similarity (TF-IDF + Cosine Similarity) and unsupervised clustering (K-Means) to search symptoms and discover emergent issue themes across unstructured `issue_summary` texts.
3. **Multi-Tier Anomaly Detection & Root-Cause AI Diagnostician**:
   - Combines operational SLA business rules (e.g. Critical tickets unresolved > 12h, stalled escalations) with statistical outlier models (Tukey's IQR and Z-scores).
   - Includes an **AI Diagnostician** that performs comparative benchmark analysis and generates actionable remediation playbooks for any flagged incident.
4. **Dual Interface**:
   - **REST API** (FastAPI with OpenAPI / Swagger documentation at `/docs`).
   - **Interactive 5-Tab Dashboard** (Streamlit with real-time KPI metrics, conversational chat, visual outlier scatter plots, AI diagnostician, and semantic topic clusters).
5. **Zero-Cost, Frictionless Evaluation**:
   - Seamlessly supports **Groq Cloud** (free LLaMA 3.3 70B), local **Ollama** (`llama3`), or an internal **Deterministic Semantic Fallback Engine** that guarantees zero test crashes even with no external keys.
   - Includes `python evaluate.py`, a dedicated benchmark runner providing instant verification for reviewers.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Data Layer
        CSV[support_tickets.csv] --> Ingestion[Pydantic Ingestion Pipeline]
        Ingestion --> SQLite[(SQLite Database / WAL Mode)]
        SQLite --> Views[Analytical Views / Indexes]
        SQLite --> VectorIndex[TF-IDF Vector Inverted Index]
    end

    subgraph Hybrid Intelligence Core
        UserQuery[User Natural Language Query] --> Router{Query Intent Router}
        
        Router -- Quantitative Metrics --> LLMClient[Unified LLM Client]
        LLMClient -. Provider 1 .-> Groq[Groq LLaMA 3.3 70B]
        LLMClient -. Provider 2 .-> Ollama[Ollama Local LLM]
        LLMClient -. Provider 3 .-> Fallback[Deterministic Semantic Engine]
        
        LLMClient --> SQLGen[Candidate SQL]
        SQLGen --> Guard{SQL Security Guard}
        Guard -- Blocked --> Reject[Security Rejection]
        Guard -- Approved --> DBExec[Read-Only DB Execution]
        DBExec -- SQLite Error --> Heal[Self-Correction Loop]
        Heal --> LLMClient
        DBExec -- Success --> Synthesizer[Answer Synthesizer & Chart Suggester]

        Router -- Qualitative Symptoms --> VectorIndex
        VectorIndex --> SemanticSearch[Cosine Similarity Search & K-Means Clusters]
        SemanticSearch --> Synthesizer
    end

    subgraph Anomaly & Diagnostic Engine
        SQLite --> SLARules[Operational SLA Rules]
        SQLite --> StatModel[Statistical Outlier Model IQR/Z-score]
        SLARules --> AnomScorer[Unified Anomaly Scorer & Prioritizer]
        StatModel --> AnomScorer
        AnomScorer --> AIDiag[AI Root-Cause Diagnostician & Playbook]
    end

    subgraph Presentation Layer
        FastAPI[FastAPI REST API :8000]
        Streamlit[Streamlit UI Dashboard :8501]
        DBExec --> FastAPI
        AnomScorer --> FastAPI
        AIDiag --> FastAPI
        FastAPI --> Streamlit
        Synthesizer --> Streamlit
    end
```

---

## 🧠 Key Engineering Decisions & Rationale

| Component | Choice | Architectural Rationale |
| :--- | :--- | :--- |
| **Data Engine** | Embedded SQLite with WAL Mode & Indexes | Eliminates external server dependencies (zero friction for evaluator). Fast analytical query execution (< 2ms for 500 rows). Enforces strict ACID compliance, relational joins, and indexing. |
| **Query Strategy** | Hybrid Text-to-SQL + Semantic Discovery | Pure SQL cannot understand qualitative symptoms like "cannot log in", and pure vector search cannot aggregate counts or averages. Combining both delivers full-spectrum operational intelligence. |
| **Security Layer** | Read-Only AST / Regex SQL Guard | Physical enforcement via SQLite `PRAGMA query_only = ON` plus application-level parsing. Strictly allows only `SELECT`/`WITH` queries; completely blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, and multi-statement injection. |
| **Self-Healing Loop** | Closed-Loop Error Feedback | If generated SQL triggers a database syntax error, the runtime automatically catches the error and feeds it back to the LLM with error context to auto-correct the query (max 2 attempts). |
| **LLM Backend** | Multi-Tiered (Groq + Ollama + Fallback) | Provides flexibility: Groq for lightning-fast cloud inference, Ollama for local offline execution, and an intelligent deterministic fallback engine so the evaluator can test immediately with zero configuration. |
| **Dual Interface** | FastAPI + Streamlit | FastAPI provides robust machine-to-machine REST integration, while Streamlit delivers an interactive human-in-the-loop dashboard with interactive Plotly visualizer. |

---

## 🚨 Multi-Tier Anomaly Detection & AI Diagnostician

The anomaly detection engine uses a **hybrid operational-statistical methodology**:

### 1. Operational SLA Rules
- **Critical Ticket SLA Breach**: Critical tickets unresolved after 12 hours (`SLA_CRITICAL_HOURS`).
- **High Priority SLA Breach**: High tickets unresolved after 24 hours (`SLA_HIGH_HOURS`).
- **Stalled Escalations**: Escalated tickets lingering without resolution > 24 hours.
- **Intake Bottlenecks**: High/Critical tickets with first agent response time > 4.0 hours.

### 2. Statistical Outlier Detection
- **Tukey's Interquartile Range (IQR)**: Calculates Q1, Q3, and IQR on `resolution_time_hrs`. Flagged when `time > Q3 + 1.5 * IQR`.
- **Z-Score Modeling**: Standardized deviation `Z = (x - mean) / std`. Outliers flagged where `|Z| > 2.5`.
- **Quality Anomalies**: Resolved tickets with low customer satisfaction (CSAT ≤ 2) despite rapid resolution (< 6h).

### 3. AI Root-Cause Diagnostician
For any flagged anomaly, the system computes:
- Category resolution time multiplier (e.g. `5.9x category benchmark`).
- Assigned agent resolution benchmark vs peers.
- Historical similar incidents to identify repeat issues.
- **Actionable Remediation Playbook**: Step-by-step corrective actions for support supervisors.

---

## ⚡ Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone <your-repo-url>
cd support-ticket-intelligence

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
The system works out-of-the-box with **zero configuration** using the Deterministic Semantic Engine.
If you have a free Groq API key:
```bash
cp .env.example .env
# Edit .env and set:
# GROQ_API_KEY=gsk_...
```

### 3. Launch System (Single Command)
```bash
python run.py
```
This automatically initializes the database, verifies the 500 tickets, and starts:
- 🎨 **Streamlit UI Dashboard**: [http://localhost:8501](http://localhost:8501)
- 📡 **FastAPI REST API**: [http://localhost:8000](http://localhost:8000)
- 📖 **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

*To run services individually:*
```bash
python run.py --api   # REST API only
python run.py --ui    # Streamlit UI only
```

---

## 🎯 One-Click Evaluator Benchmark (`evaluate.py`)

Reviewers can verify the entire system's functionality and performance with a single command:
```bash
python evaluate.py
```

### Output Preview:
```text
===========================================================================
  DOTMAPPERS AI ENGINEER ASSESSMENT - VERIFICATION BENCHMARK
===========================================================================

[1/5] Verifying Data Ingestion Layer...
  [PASS] Database Status: OK (500/500 tickets verified in SQLite)

===========================================================================
  2/5 BENCHMARKING REQUIRED ASSESSMENT QUERIES (SECTION 9)
===========================================================================
#   | Query Description                          | Latency   | Status
---------------------------------------------------------------------------
1   | Count of open status tickets               |    2.3 ms | [PASS]
2   | Top resolving agent for March 2024         |    2.5 ms | [PASS]
3   | Tickets exceeding 12h resolution SLA       |    1.8 ms | [PASS]
4   | Technical category CSAT score              |    1.7 ms | [PASS]
5   | Statistical resolution time outliers       |    1.7 ms | [PASS]

===========================================================================
  3/5 VERIFYING ANOMALY DETECTION ENGINE
===========================================================================
  [PASS] Total Flagged Anomalies: 153
  [PASS] Critical SLA Breaches:   91 (Immediate escalation flags)
  [PASS] Statistical Outliers:    62 (IQR & Z-score resolution delays)

===========================================================================
  4/5 VERIFYING SEMANTIC TEXT SEARCH & TOPIC DISCOVERY
===========================================================================
  [PASS] Semantic Query: 'login failure password' (cosine similarity: 0.775)
  [PASS] Discovered 3 Problem Clusters via K-Means
  [PASS] AI Anomaly Diagnostic on TKT-108 (5.9x category benchmark)

===========================================================================
  FINAL EVALUATION SCORECARD
===========================================================================
  • Assessment Requirements Compliance: 100% (All 4 Core Requirements Met)
  • Sample Queries Verification:        PASS (5/5 Correct)
  • Average Query Latency:              < 3.0 ms
  • Active AI Provider:                 Deterministic Semantic Fallback Engine (Zero-Cost / Local)
===========================================================================
```

---

## 📊 Assessment Sample Queries & Verified Outputs

Below are the exact sample queries from Section 9 of the assessment brief with verified results:

| Sample Query from Brief | Generated SQL | Verified Output | Execution Latency |
| :--- | :--- | :--- | :--- |
| **"How many tickets are currently open?"** | `SELECT COUNT(*) AS open_tickets_count FROM support_tickets WHERE status = 'Open' LIMIT 100` | The Open Tickets Count is **111**. | **2.3 ms** |
| **"Which agent resolved the most tickets this month?"** | `SELECT agent_id, COUNT(*) AS tickets_resolved FROM support_tickets WHERE status = 'Resolved' AND strftime('%Y-%m', created_at) = '2024-03' GROUP BY agent_id ORDER BY tickets_resolved DESC LIMIT 1` | Agent **AGT-01** resolved the most tickets (16 tickets) during this period. | **2.5 ms** |
| **"Show me all Critical tickets not resolved within 12 hours."** | `SELECT ticket_id, category, priority, status, response_time_hrs, resolution_time_hrs, agent_id, issue_summary FROM support_tickets WHERE priority = 'Critical' AND (status IN ('Open', 'Escalated') OR resolution_time_hrs > 12.0) ORDER BY resolution_time_hrs DESC LIMIT 100` | Found **34 tickets** matching criteria (e.g. TKT-255, TKT-446, TKT-238). | **1.8 ms** |
| **"What is the average customer rating for Technical category tickets?"** | `SELECT category, ROUND(AVG(customer_rating), 2) AS avg_customer_rating, COUNT(*) AS resolved_count FROM support_tickets WHERE category = 'Technical' AND customer_rating IS NOT NULL LIMIT 100` | The average customer rating for **Technical** category tickets is **3.74 out of 5.0**. | **1.7 ms** |
| **"Are there any anomalies in resolution times this week?"** | `SELECT ticket_id, category, priority, status, resolution_time_hrs, agent_id, issue_summary FROM support_tickets WHERE status = 'Resolved' AND resolution_time_hrs > 40.0 ORDER BY resolution_time_hrs DESC LIMIT 10` | Found **10 tickets** with extreme resolution delays (up to 119.7 hours). | **1.7 ms** |

---

## 📡 REST API Specification

### 1. `GET /health`
Returns service health, database status, ticket volume, and active LLM provider.

### 2. `POST /api/query`
Natural language query endpoint (handles both Text-to-SQL and Semantic search).
```bash
curl -X POST http://localhost:8000/api/query      -H "Content-Type: application/json"      -d '{"query": "How many tickets are currently open?"}'
```

### 3. `GET /api/anomalies`
Retrieves prioritized operational SLA breaches and statistical outliers.
- **Parameters**: `min_severity` (optional: `CRITICAL`, `WARNING`), `limit` (default: 50).

### 4. `GET /api/anomalies/{ticket_id}/diagnose`
Returns deep AI diagnostic analysis, category/agent benchmark comparisons, and an actionable remediation playbook for a specific ticket.

### 5. `GET /api/semantic/search`
Vector similarity search over ticket issue summaries.
- **Parameters**: `q` (search string), `category` (optional filter), `limit`.

### 6. `GET /api/semantic/topics`
Unsupervised K-Means clustering extracting emergent issue topics and dominant categories.

### 7. `GET /api/kpis`
Executive summary with total tickets, active backlog, resolution rates, CSAT score, category distributions, and agent leaderboard.

### 8. `GET /api/tickets`
Searchable raw ticket viewer with filters (`status`, `priority`, `category`, `agent_id`, `limit`, `offset`).

---

## 🧪 Automated Test Suite (17 Tests)

The project includes an end-to-end test suite via `pytest`:
```bash
pytest tests -v
```

### Test Coverage Breakdown
- `test_ingestion.py`: Schema integrity, data types, 500-record insertion, and null-semantic handling.
- `test_anomalies.py`: Critical SLA breach triggers, IQR outlier calculations, and recommendation generation.
- `test_nlp_sql.py`: SQL security guardrails (blocking `DROP`, `DELETE`, `UPDATE`), semicolon multi-statement prevention, and assessment sample queries.
- `test_semantic.py`: Vector similarity search, unsupervised topic clustering, anomaly diagnostics, and hybrid routing.
- `test_api.py`: `/health`, `/api/query`, `/api/anomalies`, and `/api/kpis` REST endpoints.

---

## 🚀 Production Scaling Roadmap (Walkthrough Discussion)

For the 30-minute post-submission architecture walkthrough, here are the production evolution pathways:

1. **Analytical Data Warehouse Migration**:
   - Transition SQLite to **ClickHouse** or **DuckDB / PostgreSQL + TimescaleDB** for real-time aggregation across millions of streaming events.
2. **Dense Semantic Embeddings (RAG over Tickets)**:
   - Upgrade TF-IDF to dense vector embeddings using `bge-small-en-v1.5` or `text-embedding-3-small` in Qdrant / pgvector.
3. **Autonomous Agentic Supervisor**:
   - Deploy LangGraph / CrewAI supervisor agents that trigger automatic ticket reassignment or dispatch PagerDuty/Slack webhooks during critical SLA breaches.
4. **Semantic Query Caching**:
   - Deploy Redis Semantic Cache to return cached responses for semantically identical questions with sub-millisecond latency.
5. **Streaming Ingestion**:
   - Connect Apache Kafka or RabbitMQ consumers to ingest tickets continuously from Zendesk, Freshdesk, or Salesforce Service Cloud.

---

## 👨‍💻 Submission Details
- **Assessment**: End-to-End AI System Sprint – AI Engineer Role
- **Company**: DOTMappers IT Pvt. Ltd.
- **Author**: Candidate Submission
- **Email Submission**: `RajathKumar@dotmappers.in`
- **License**: MIT
