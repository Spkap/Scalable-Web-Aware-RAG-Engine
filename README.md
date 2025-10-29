# WebRAG - Scalable Web-Aware RAG Engine

> A production-oriented Retrieval-Augmented Generation (RAG) engine for web content, optimized with Google Gemini embeddings (gemini-embedding-001 @ 1536 dimensions) and Gemini 2.5 Flash LLM.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [High-Level System Diagram](#high-level-system-diagram)
  - [Component Interaction](#component-interaction)
- [Technology Stack](#technology-stack)
  - [Core Technologies Table](#core-technologies-table)
  - [Why 1536 Dimensions?](#why-1536-dimensions)
- [System Design](#system-design)
  - [Architecture Patterns](#architecture-patterns)
  - [Project Structure](#project-structure)
- [Database Schemas](#database-schemas)
  - [PostgreSQL Schema](#postgresql-schema)
  - [Qdrant Configuration](#qdrant-configuration)
- [API Documentation](#api-documentation)
  - [Endpoints Overview Table](#endpoints-overview-table)
  - [POST /ingest-url](#1-post-ingest-url)
  - [POST /query](#2-post-query)
  - [GET /status/{job_id}](#3-get-statusjob_id)
  - [GET /health](#4-get-health)
  - [GET /docs](#5-get-docs)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Step 1: Clone Repository](#step-1-clone-repository)
  - [Step 2: Environment Configuration](#step-2-environment-configuration)
  - [Step 3: Start Services](#step-3-start-services)
  - [Step 4: Verify Health](#step-4-verify-health)
  - [Accessing Services](#accessing-services)
- [Usage Examples](#usage-examples)
  - [Ingest a Wikipedia Article](#example-1-ingest-wikipedia-article)
  - [Check Processing Status](#example-2-check-processing-status)
  - [Query Knowledge Base](#example-3-query-knowledge-base)
- [Design Decisions](#design-decisions)
  - [Why Gemini embedding-001 with 1536 Dimensions?](#why-gemini-embedding-001-with-1536-dimensions)
  - [Why Async Architecture?](#why-async-architecture)
  - [Why Qdrant over FAISS/ChromaDB?](#why-qdrant-over-faisschromadb)
  - [Why PostgreSQL for Metadata?](#why-postgresql-for-metadata)
  - [Chunking Strategy](#chunking-strategy)
- [Scalability & Production](#scalability--production)
  - [Horizontal Scaling](#horizontal-scaling)
  - [Performance Optimization](#performance-optimization)
  - [Monitoring](#monitoring)
  - [Security Considerations](#security-considerations)
- [Testing](#testing)
  - [Integration Tests](#integration-tests)
  - [Manual Testing](#manual-testing)
- [Demo Video](#demo-video)
- [Future Improvements](#future-improvements)
- [Technical Highlights](#technical-highlights)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contact](#contact)

## Overview

WebRAG is a scalable, web-aware Retrieval-Augmented Generation engine built as an end-to-end demonstration for AiRA's technical assessment (October 2025). It ingests web pages, converts them into high-quality vector embeddings using Google Gemini embedding-001 (configured to 1536 dimensions), stores vectors in Qdrant, and serves queries via a FastAPI-based HTTP API. The ingestion pipeline is asynchronous (FastAPI + Celery + Redis) to ensure responsive user interactions and robust background processing.

Key features:

- Async-first ingestion pipeline with Celery + Redis for durable background jobs
- High-quality embeddings via gemini-embedding-001 with output_dimensionality=1536
- Vector storage in Qdrant (1536-dim vectors, cosine similarity, HNSW index)
- Gemini 2.5 Flash LLM for answer generation & re-ranking
- PostgreSQL for job metadata and audit trails
- Docker Compose deployment for reproducible environments
- Full API docs, curl examples, health checks, and monitoring hooks

Built for AiRA assessment, October 2025.

## Architecture

### High-Level System Diagram

Below is a Mermaid diagram showing the system components and data flows. It illustrates client interactions, FastAPI server, Redis, Celery workers, PostgreSQL, Qdrant, and Google Gemini APIs.

```mermaid
flowchart LR
  subgraph Client
    A[User / Client] -->|HTTP| B[FastAPI API]
  end

  B -->|POST ingest-url| C[Enqueue Job in Redis]
  B -->|POST query| D[Query Handler]
  B -->|GET /status| E[Status Handler]

  C -->|Redis Queue| F[Celery Worker 1]
  C -->|Redis Queue| G[Celery Worker 2]
  F -->|fetch url & chunk| H[Content Processor]
  G -->|embed chunks| I[Embeddings Service]

  H -->|chunks| I
  I -->|embeddings (1536-d)| J[Qdrant Vector DB]
  H -->|metadata| K[PostgreSQL]

  D -->|top_k vectors| J
  J -->|nearest neighbors| L[Re-ranker & Generator]
  L -->|call| M[Gemini 2.5 Flash API]
  L -->|return| B

  K ---|job status| E

  subgraph Google
    I2[Gemini Embedding API\n(gemini-embedding-001, 1536-d)]
    M2[Gemini 2.5 Flash\n(LLM)]
  end

  I -->|API calls| I2
  L -->|API calls| M2

  style J fill:#f9f,stroke:#333,stroke-width:1px
  style K fill:#bbf,stroke:#333,stroke-width:1px
  style F fill:#efe,stroke:#333,stroke-width:1px
  style G fill:#efe,stroke:#333,stroke-width:1px
```

### Component Interaction

Ingestion pipeline (step-by-step):

1. Client POSTs a URL to `/ingest-url`.
2. FastAPI validates URL and creates an ingestion job record in PostgreSQL (`url_ingestion_jobs`) with status `pending`.
3. FastAPI enqueues a Celery task into Redis to process the job asynchronously and returns `202 Accepted` with job_id.
4. Celery worker picks up the task, downloads and sanitizes the page content.
5. Content is chunked (RecursiveCharacterTextSplitter: chunk_size=800 tokens, overlap=100 tokens).
6. Each chunk is batched and sent to the Gemini Embeddings API (gemini-embedding-001) with output_dimensionality=1536.
7. Embeddings are upserted into Qdrant with payload metadata (source_url, job_id, chunk_index, textSnippet).
8. Job status and progress are updated in PostgreSQL; retries/logging handled by Celery.

Query pipeline (step-by-step):

1. Client POSTs a `question` to `/query` with optional `top_k` and `filters`.
2. FastAPI validation, optional local Redis cache check.
3. Query text is embedded using gemini-embedding-001 (1536-dim) and sent to Qdrant for nearest neighbors.
4. Top-k chunks are retrieved, optionally re-ranked using a cross-encoder, and passed to Gemini 2.5 Flash for answer generation.
5. The API returns the generated answer with source snippets, URLs, and metadata (embedding model, dimensions, processing time).

## ASCII Block Diagrams (text-first diagrams)

The following ASCII/block diagrams provide a compact, text-first view of the system for reviewers who prefer plain-text architecture over rendered diagrams. These are intentionally exact to the project's stack and configuration.

### Client Layer & Core Components

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
│  ┌──────────────┐                        ┌──────────────┐           │
│  │   Browser    │◄──────── HTTP ─────────│  Mobile App  │           │
│  └──────────────┘                        └──────────────┘           │
└────────────────────────────────┬────────────────────────────────────┘
                 │
          ┌────────────▼────────────┐
          │     FASTAPI SERVER      │
          │   (API Gateway)         │
          │  Port: 8000             │
          │                         │
          │  Endpoints:             │
          │  • POST /ingest-url     │
          │  • POST /query          │
          │  • GET /status/{id}     │
          │  • GET /health          │
          └───┬─────────────┬───────┘
            │             │
      ┌───────────▼─┐       ┌──▼──────────────┐
      │  PostgreSQL │       │  Redis (Broker)  │
      │  (Metadata) │       │  Port: 6379      │
      │             │       │                  │
      │  Stores:    │       │  Job Queue:      │
      │  • Job Status│      │  • Pending Jobs  │
      │  • URL Info │       │  • Task Results  │
      │  • Metadata │       │                  │
      └─────────────┘       └──────┬───────────┘
                     │
                ┌────────▼────────┐
                │ CELERY WORKERS  │
                │  (Background)   │
                │                 │
                │  Tasks:         │
                │  1. Fetch URL   │
                │  2. Clean HTML  │
                │  3. Chunk Text  │
                │  4. Embed (gemini-embedding-001 @1536)
                │  5. Store       │
                └────┬────────────┘
                   │
          ┌────────────────┼────────────────┐
          │                │                │
      ┌───────▼────────┐  ┌───▼─────────┐  ┌──▼──────────┐
      │Gemini Embeddings│  │  Qdrant DB  │  │ Gemini 2.5  │
      │ API (Google)    │  │  (Vectors)  │  │ Flash (LLM) │
      │ model:          │  │             │  │             │
      │ gemini-embedding-001
      │ dims: 1536      │  │  Stores:    │  │ Used for:   │
      │                 │  │  • Vectors  │  │ • Answers   │
      │                 │  │  • Chunks   │  │ • Re-ranking│
      └─────────────────┘  └─────────────┘  └─────────────┘

```

### Ingestion Workflow (text flow)

```text
┌──────────────────────────────────────────────────────────────────┐
│                    INGESTION WORKFLOW                             │
└──────────────────────────────────────────────────────────────────┘

  USER                 FASTAPI              PostgreSQL         Redis
   │                      │                      │               │
   │  POST /ingest-url    │                      │               │
   ├─────────────────────►│                      │               │
   │  {url: "..."}       │                      │               │
   │                      │                      │               │
   │                      │  1. Validate URL     │               │
   │                      │     (format check)   │               │
   │                      │                      │               │
   │                      │  2. Create Job Entry │               │
   │                      ├─────────────────────►│               │
   │                      │  INSERT job_id,      │               │
   │                      │  status='pending'    │               │
   │                      │◄─────────────────────┤               │
   │                      │                      │               │
   │                      │  3. Push to Queue    │               │
   │                      ├──────────────────────┼──────────────►│
   │                      │  task_id = celery    │               │
   │                      │  .ingest_url.delay() │               │
   │                      │                      │               │
   │   202 Accepted       │                      │               │
   │◄─────────────────────┤                      │               │
   │  {job_id, status}    │                      │               │
   │                      │                      │               │

  Celery Worker          Gemini Embeddings    Qdrant          PostgreSQL
     │                     (Google API)        │                 │
     │  4. Dequeue Job     │                │                 │
     │◄────────────────────┤                │                 │
     │                     │                │                 │
     │  5. Update Status   │                │                 │
     ├─────────────────────┼────────────────┼────────────────►│
     │  status='processing'│                │                 │
     │                     │                │                 │
     │  6. Fetch URL       │                │                 │
     │  (requests + BS4)   │                │                 │
     │  Extract content    │                │                 │
     │                     │                │                 │
     │  7. Chunk Text      │                │                 │
     │  (RecursiveChar     │                │                 │
     │   TextSplitter)     │                │                 │
     │  → 800 token chunks │                │                 │
     │  → 100 token overlap│                │                 │
     │                     │                │                 │
     │  8. Generate Embeds │                │                 │
     ├────────────────────►│                │                 │
     │  texts=chunks[]     │                │                 │
     │  model='gemini-embedding-001'         │                 │
     │  output_dimensionality=1536           │                 │
     │◄────────────────────┤                │                 │
     │  vectors[1536-dim]  │                │                 │
     │                     │                │                 │
     │  9. Store Vectors   │                │                 │
     ├─────────────────────┼───────────────►│                 │
     │  collection='web_documents'          │                 │
     │  + metadata (job_id, chunk_index)    │                 │
     │                     │                │                 │
     │  10. Update Status  │                │                 │
     ├─────────────────────┼────────────────┼────────────────►│
     │  status='completed' │                │                 │
     │  chunk_count=N      │                │                 │
     │                     │                │                 │

```

### Query Workflow (text flow)

```text
┌──────────────────────────────────────────────────────────────────┐
│                      QUERY WORKFLOW                               │
└──────────────────────────────────────────────────────────────────┘

  USER           FASTAPI        Gemini Embeddings   Qdrant      Gemini 2.5 Flash
   │                │               (Google API)       │            (LLM)
   │  POST /query   │               model:           │            │
   ├───────────────►│               gemini-embedding-001│           │
   │  {"question": │               dims:1536       │            │
   │   "..."}       │               │             │            │
   │                │  1. Embed Question           │            │
   │                ├──────────────►│             │            │
   │                │  query_vector [1536-dim]     │            │
   │                │◄──────────────┤             │            │
   │                │               │             │            │
   │                │  2. Search Qdrant (top_k)    │            │
   │                ├─────────────────────────────►│            │
   │                │  return top-k chunks + meta  │            │
   │                │◄─────────────────────────────┤            │
   │                │  3. Build prompt (context)   │            │
   │                │     include top-k chunks     │            │
   │                │  4. Call LLM (Gemini 2.5)    │            │
   │                ├───────────────────────────────────────►│
   │                │  prompt + context                         │
   │                │◄───────────────────────────────────────┤
   │                │  grounded answer + citations              │
   │  200 OK        │               │             │            │
   │◄───────────────┤  {answer, sources[], metadata}         │
   │                │               │             │            │

```

Notes:

- Embedding model used throughout: `gemini-embedding-001` with `output_dimensionality=1536`.
- Qdrant collection name used in examples: `web_documents` (vector_size = 1536).
- The ASCII diagrams are plain-text; they are intended for inclusion directly in the README for reviewers who need text-only architecture sketches.

## Technology Stack

### Core Technologies Table

| Layer            | Technology                  | Version | Purpose                            | Justification                                                                                                        |
| ---------------- | --------------------------- | ------: | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| API Framework    | FastAPI                     |   0.95+ | HTTP API, request validation, docs | Async, high-performance ASGI framework widely adopted for Python microservices                                       |
| Async Worker     | Celery                      |     5.x | Background tasks, retries          | Proven distributed task queue; integrates with Redis and supports retries/pooling                                    |
| Message Broker   | Redis                       |     7.x | Celery broker & cache              | Fast in-memory broker; used for queueing and caching                                                                 |
| Embeddings       | Google Gemini embedding-001 |  stable | Generate 1536-dim embeddings       | **Gemini embedding-001 (1536 dimensions)** — optimal quality/storage balance; configurable via output_dimensionality |
| LLM              | Gemini 2.5 Flash            |  stable | Answer generation & re-ranking     | High-quality generative model integrated via Google API                                                              |
| Vector DB        | Qdrant                      |     1.x | Store & search vectors             | Production-ready vector DB with metadata filters & REST API; supports 1536-dim vectors                               |
| Metadata DB      | PostgreSQL                  |    15.x | Job & metadata persistence         | ACID, JSONB support, strong query capabilities                                                                       |
| Containerization | Docker & Docker Compose     |     24+ | Reproducible deployment            | Simple one-command deployment for dev & staging                                                                      |
| Monitoring       | Flower, health endpoint     |       - | Monitor Celery & services          | Operational observability for queue & workers                                                                        |

CRITICAL: In the Embeddings row, note explicitly:

- Technology: Google Gemini embedding-001
- Dimensions: 1536 (configurable via output_dimensionality)
- Justification: Optimal balance of quality (MTEB score 68.17) and storage efficiency (50% reduction vs 3072-dim). Google ecosystem integration with Gemini 2.5 Flash LLM.

### Why 1536 Dimensions?

- MTEB benchmark: 1536-dim achieves the same reported score (68.17) as 3072-dim according to Google's technical documentation and internal benchmarks.
- Storage savings: 1536 is 50% smaller than 3072, cutting vector storage and network egress costs nearly in half.
- Performance: Empirically, embeddings at 1536 maintain quality comparable to higher dimensions for retrieval tasks in common benchmarks.
- Cost optimization: Lower memory and compute usage in Qdrant and embedding batches.
- Reference: https://ai.google.dev/gemini-api/docs/embeddings

## System Design

### Architecture Patterns

1. Async-first design: FastAPI responds immediately (202) for ingestion requests, while Celery performs I/O-heavy work in the background.
2. Separation of concerns: API, ingestion, embedding, vector storage, and generation are decoupled and can be scaled independently.
3. Error handling strategy: Retries with exponential backoff in Celery; durable job state in PostgreSQL; idempotent upserts into Qdrant.
4. Scalability approach: Horizontal scaling of Celery workers, read replicas for PostgreSQL, and sharding/replication in Qdrant for large datasets.

### Project Structure

```
webrag/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application
│   ├── config.py              # configuration & env parsing
│   ├── database.py            # SQLAlchemy / DB setup
│   ├── celery_app.py          # Celery app factory
│   ├── models.py              # ORM models (url_ingestion_jobs, etc.)
│   ├── services/
│   │   ├── content_processor.py
│   │   ├── embeddings.py      # Gemini embedding client wrapper
│   │   ├── llm.py             # Gemini 2.5 Flash wrapper
│   │   └── vectorstore.py     # Qdrant client wrapper
│   ├── tasks/
│   │   └── ingestion.py       # Celery tasks for ingestion
│   └── utils/
│       ├── logger.py
│       └── validators.py
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── up.sh
├── scripts/
│   └── init_db.sql
├── tests/
│   └── test_integration.py
├── requirements.txt
└── README.md
```

## Database Schemas

### PostgreSQL Schema

Below is the CREATE TABLE statement for `url_ingestion_jobs` used to track ingestion jobs, progress, and metadata.

```sql
CREATE TABLE url_ingestion_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  chunk_count INTEGER DEFAULT 0,
  processed_chunks INTEGER DEFAULT 0,
  error TEXT NULL,
  metadata JSONB DEFAULT '{}',
  CONSTRAINT url_not_empty CHECK (length(url) > 0)
);

-- Indexes
CREATE INDEX idx_url_ingestion_jobs_status ON url_ingestion_jobs(status);
CREATE INDEX idx_url_ingestion_jobs_created_at ON url_ingestion_jobs(created_at);
```

Sample record (JSON):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
  "status": "completed",
  "created_at": "2025-10-15T12:34:56Z",
  "updated_at": "2025-10-15T12:35:31Z",
  "chunk_count": 18,
  "processed_chunks": 18,
  "metadata": {
    "domain": "en.wikipedia.org",
    "ingestion_time_seconds": 35.4
  }
}
```

### Qdrant Configuration

Qdrant collection configuration used by this project. Note the vector size: 1536 (gemini-embedding-001 with output_dimensionality=1536).

```json
{
  "name": "web_documents",
  "vector_size": 1536,
  "distance": "Cosine",
  "shards": 1,
  "replication_factor": 1,
  "hnsw_config": {
    "m": 16,
    "ef_construct": 100,
    "full_scan_threshold": 100
  }
}
```

Point structure (example payload):

```json
{
  "id": "<uuid-or-int>",
  "vector": [0.00123, -0.00234, ... 1536 values ...],
  "payload": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_url": "https://en.wikipedia.org/...",
    "chunk_index": 3,
    "text": "...chunk text...",
    "embedding_model": "gemini-embedding-001",
    "embedding_dimensions": 1536
  }
}
```

## API Documentation

### Endpoints Overview Table

| Method | Path             | Description                                         |
| ------ | ---------------- | --------------------------------------------------- |
| POST   | /ingest-url      | Enqueue a URL to be ingested asynchronously         |
| POST   | /query           | Query the RAG knowledge base and generate an answer |
| GET    | /status/{job_id} | Check ingestion job status and progress             |
| GET    | /health          | Health check for system components                  |
| GET    | /docs            | FastAPI interactive docs (Swagger UI)               |

### 1. POST /ingest-url

**Description:** Enqueue a URL for asynchronous ingestion. The request is validated and a job record is created in PostgreSQL; the actual work is handled by Celery workers.

**Request Body:**

```json
{
  "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
  "metadata": { "source": "user" }
}
```

**Response: 202 Accepted**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "URL queued for processing"
}
```

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}'
```

**Error Responses:**

- 400: Invalid URL or missing required fields
- 500: Internal error (e.g., DB or Redis unavailable)

### 2. POST /query

**Description:** Query the knowledge base with a natural language question. Returns generated answer, source snippets, and metadata.

**Request Body:**

```json
{
  "question": "What is retrieval augmented generation?",
  "top_k": 5,
  "filters": { "domain": "en.wikipedia.org" }
}
```

**Response:**

```json
{
  "answer": "Retrieval Augmented Generation (RAG) is a technique that...",
  "sources": [
    {
      "text": "RAG combines retrieval with generation...",
      "source_url": "https://en.wikipedia.org/wiki/RAG",
      "relevance_score": 0.8934
    }
  ],
  "metadata": {
    "embedding_model": "gemini-embedding-001",
    "embedding_dimensions": 1536,
    "llm_model": "gemini-2.5-flash",
    "processing_time_ms": 1240
  }
}
```

**cURL Example:**

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is retrieval augmented generation?","top_k":5}'
```

**Notes on metadata:**

All query responses include a `metadata` object with at minimum:

- embedding_model: "gemini-embedding-001"
- embedding_dimensions: 1536
- llm_model: "gemini-2.5-flash"
- processing_time_ms: integer

### 3. GET /status/{job_id}

**Description:** Retrieve the ingestion job status and progress metrics.

**Response (example - completed):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "chunk_count": 18,
  "processed_chunks": 18,
  "processing_time_seconds": 35.4
}
```

**cURL Example:**

```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

### 4. GET /health

**Description:** Health endpoint ensuring downstream services are reachable and workers are up.

**Response (example):**

```json
{
  "status": "healthy",
  "services": {
    "postgres": "connected",
    "redis": "connected",
    "qdrant": "connected",
    "celery_workers": 2
  }
}
```

**cURL Example:**

```bash
curl http://localhost:8000/health
```

### 5. GET /docs

FastAPI interactive Swagger/OpenAPI UI available at `/docs` when running locally.

## Setup Instructions

### Prerequisites

- Docker 24+ and Docker Compose
- Python 3.10+ (for local development without Docker)
- Google AI API Key (for Gemini embedding & LLM)
- Optional: Qdrant desktop/dashboard or managed Qdrant instance

### Step 1: Clone Repository

```bash
git clone <repo-url>
cd webrag
```

### Step 2: Environment Configuration

Copy the example environment file and edit values.

```bash
cp .env.example .env
```

Add the following values to `.env`:

```
# Google API
GOOGLE_API_KEY=your_google_api_key_here

# Postgres
POSTGRES_USER=raguser
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=webrag_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=web_documents

# Embedding settings
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=1536 # Critical: using 1536 for optimal quality/storage
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# LLM settings
LLM_MODEL=gemini-2.5-flash
```

Include any provider-specific options or proxy configuration if required by your network.

### Step 3: Start Services

Build and start with Docker Compose (from `webrag/docker` or root depending on compose file path):

```bash
# from the `webrag/docker` directory (recommended)
docker compose -f docker-compose.yml --env-file ../.env up --build

# or in detached mode
docker compose -f docker-compose.yml --env-file ../.env up -d --build
```

### Step 4: Verify Health

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{
  "status": "healthy",
  "services": {
    "postgres": "connected",
    "redis": "connected",
    "qdrant": "connected",
    "celery_workers": 2
  }
}
```

### Accessing Services

- API: http://localhost:8000
- Interactive Docs (Swagger UI): http://localhost:8000/docs
- Celery Flower (if enabled): http://localhost:5555
- Qdrant Dashboard: http://localhost:6333/dashboard

## Usage Examples

### Example 1: Ingest Wikipedia Article

Submit URL for ingestion:

```bash
curl -X POST "http://localhost:8000/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}'
```

Response:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "URL queued for processing"
}
```

### Example 2: Check Processing Status

```bash
curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
```

Response (completed):

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "chunk_count": 18,
  "processing_time_seconds": 35.4
}
```

### Example 3: Query Knowledge Base

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is retrieval augmented generation?","top_k": 5}'
```

Response:

```json
{
  "answer": "Retrieval Augmented Generation (RAG) is...",
  "sources": [
    {
      "text": "RAG combines retrieval with generation...",
      "source_url": "https://en.wikipedia.org/wiki/RAG",
      "relevance_score": 0.8934
    }
  ],
  "metadata": {
    "embedding_model": "gemini-embedding-001",
    "embedding_dimensions": 1536,
    "processing_time_ms": 1240
  }
}
```

## Design Decisions

### 1. Why Gemini embedding-001 with 1536 Dimensions?

**Decision:** Use gemini-embedding-001 with output_dimensionality=1536.

**Rationale:**

- **Quality:** MTEB score of 68.17—empirically equivalent to 3072 dimensions for retrieval tasks.
- **Efficiency:** 1536 provides ~50% lower storage footprint vs 3072-dim vectors.
- **Cost:** Reduced memory and compute costs for vector storage and similarity search.
- **Ecosystem:** Native integration and compatibility with Gemini 2.5 Flash LLM.
- **Practicality:** Faster batch embedding throughput and lower network egress for embeddings transfers.

**Benchmark Evidence:** Based on Google's public embedding APIs and MTEB results, 1536-dim embeddings match the 3072-dim score (68.17) while reducing storage by half.

### 2. Why Async Architecture?

**Decision:** FastAPI for the HTTP layer + Celery + Redis for background processing.

**Rationale:**

- AiRA requested async systems.
- Ensures non-blocking calls: ingestion returns quickly while work is done in background.
- Workers are horizontally scalable and can be monitored with Flower.

### 3. Why Qdrant over FAISS/ChromaDB?

**Decision:** Qdrant chosen for vector storage and retrieval.

**Comparison:**

| Feature            | Qdrant |                                      FAISS | ChromaDB |
| ------------------ | -----: | -----------------------------------------: | -------: |
| Production-ready   |     ✅ |                            ⚠️ (needs glue) |       ✅ |
| Metadata filtering |     ✅ |                                         ❌ |       ✅ |
| Persistence        |     ✅ | ❌ (index persistence requires extra work) |       ✅ |
| REST API           |     ✅ |                                         ❌ |       ✅ |
| 1536-dim support   |     ✅ |                                         ✅ |       ✅ |

Qdrant provides a managed-like developer experience with persistence, metadata filters, and an HTTP API that simplifies integration.

### 4. Why PostgreSQL for Metadata?

**Decision:** PostgreSQL for ingestion job metadata and audit trails.

**Rationale:**

- ACID guarantees for job state transitions
- Powerful querying (indexed fields + JSONB)
- Reliability and easy backup / restore

### 5. Chunking Strategy

**Configuration:**

- Chunk size: 800 tokens
- Overlap: 100 tokens
- Splitter: RecursiveCharacterTextSplitter

**Rationale:** Keeps chunks within common context windows, overlap prevents information loss at boundaries, and recursive splitting preserves semantic coherence.

## Scalability & Production

### Horizontal Scaling

Scale Celery workers on demand (from repo root):

```bash
docker compose -f docker/docker-compose.yml up --scale worker=5 -d
```

Database and Qdrant scaling:

- PostgreSQL: connection pooling, read replicas for analytics and status endpoints
- Qdrant: horizontal sharding or managed clustering for >1M documents

### Performance Optimization

- Batch embedding generation (batch up to 128 chunks per API call)
- Redis caching for frequent/expensive queries
- Async I/O everywhere to avoid thread blocking
- HNSW tuning in Qdrant: m=16, ef_construct=100, ef_search tunable per-query

### Monitoring

- Health endpoint `/health` for system-level checks
- Celery Flower dashboard for task monitoring
- Structured JSON logging and request tracing (job_id propagated)

### Security Considerations

- Store API keys in environment variables; never commit to source control
- Input validation on all endpoints (use pydantic models)
- Use SQLAlchemy ORM to minimize risk of SQL injection
- Rate limiting and authentication are planned enhancements

## Testing

### Integration Tests

Run the integration test suite:

```bash
python -m pytest tests/test_integration.py -v
```

Expected tests (all passing):

- test_01_health_check - All services healthy
- test_02_ingest_url - Job created successfully
- test_03_check_job_status - Status tracking works
- test_04_wait_for_completion - Ingestion completes
- test_05_query_knowledge_base - RAG pipeline functional
- test_06_query_with_filters - Filtering works
- test_07_invalid_url_ingestion - Validation works
- test_08_empty_query - Error handling works
- test_09_query_nonexistent_content - Graceful handling

### Manual Testing

Test ingestion:

```bash
curl -X POST http://localhost:8000/ingest-url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Test query:

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"test query"}'
```

## Demo Video

📹 **Demo Video:** [Link to 5-10 minute video]

**Video Contents:**

1. Architecture overview (1 min)
2. Starting services with Docker (1 min)
3. Ingesting URL via /ingest-url (2 min)
4. Monitoring with /status and Flower (1 min)
5. Querying with /query endpoint (2 min)
6. Showing Qdrant vectors (1536-dim) (1 min)
7. Design decisions explanation (1-2 min)

## Future Improvements

1. Hybrid Search (BM25 + semantic) for improved precision
2. Query caching in Redis for hot queries
3. Semantic chunking based on topics or headings
4. Re-ranking with cross-encoder models
5. JWT-based authentication & multi-tenant support
6. Rate limiting per user
7. Batch ingestion of multiple URLs in a single request
8. Web UI for non-technical users (React)
9. Prometheus + Grafana for metrics and alerting
10. A/B testing for embedding dimensionality and re-ranking strategies

## Technical Highlights

1. ✅ Optimal Embedding Configuration: gemini-embedding-001 @ 1536 dimensions — full quality, half storage
2. ✅ True Async Architecture: Non-blocking FastAPI endpoints with Celery background workers
3. ✅ Production Patterns: Retry logic, idempotency, and structured logging
4. ✅ Comprehensive Testing: Integration tests validating end-to-end pipeline
5. ✅ Container-first: Docker Compose for reproducible local and staging environments

## Troubleshooting

### Issue: "Embedding dimension mismatch"

**Solution:** Verify `EMBEDDING_DIMENSION=1536` in `.env` and ensure Qdrant collection `vector_size` is 1536.

### Issue: "No documents found"

**Solution:** Check `/status/{job_id}` for ingestion completion and verify Qdrant contains points for the job_id.

### Issue: "API quota exceeded"

**Solution:** Check Google API dashboard and add retry/backoff logic or upgrade quota.

### Issue: "Workers not processing"

**Solution:** Ensure Redis connection and Celery workers are running. Check Flower and Celery logs.

## License

MIT License

## Contact

**Project:** WebRAG - AiRA Technical Assessment  
**Date:** October 2025

---
