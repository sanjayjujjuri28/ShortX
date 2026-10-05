# 🔗 ShortX — High-Performance URL Shortener & Analytics

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live%20Demo-shortx--95k9.onrender.com-00C7B7?style=for-the-badge&logo=render&logoColor=white)](https://shortx-95k9.onrender.com)

### 🌐 **Live Application:** [https://shortx-95k9.onrender.com](https://shortx-95k9.onrender.com)
📚 **Interactive Swagger API Docs:** [https://shortx-95k9.onrender.com/docs](https://shortx-95k9.onrender.com/docs)

<br/>

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Pytest-17%20Passed-success?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**A production-grade, minimalist URL shortening and analytics platform engineered to showcase core Software Development Engineer (SDE) backend principles.**

[🌐 Live Demo](https://shortx-95k9.onrender.com) • [User Flow](#-user-flow) • [System Architecture](#-system-architecture) • [Redis Deep Dive](#-redis-engineering-decisions) • [API Reference](#-api-architecture) • [Getting Started](#-getting-started)

</div>

---

## 📌 Executive Summary

**ShortX** solves high-throughput URL shortening and click tracking through a layered backend architecture. Instead of treating Redis merely as a buzzword, ShortX implements **real Redis cache-aside redirection**, **distributed atomic rate limiting**, **cache invalidation on deletion**, and **time-series click aggregation**, paired with a dark glassmorphic single-page dashboard.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **API Framework** | **FastAPI** | High-concurrency async endpoints, automatic OpenAPI docs, Pydantic V2 validation |
| **Primary Database** | **PostgreSQL 16** | ACID-compliant relational storage for users, URLs, and time-series click events |
| **ORM** | **SQLAlchemy 2.0** | Declarative models, relationship cascading, session pooling |
| **In-Memory Cache** | **Redis 7** | Sub-5ms short code resolution, atomic rate limiting, cache eviction |
| **Security & Auth** | **Bcrypt & PyJWT** | Salted password hashing, stateless JSON Web Token authentication |
| **Containerization** | **Docker & Compose** | Multi-container orchestration (App, PostgreSQL, Redis) with health checks |
| **Frontend** | **Vanilla HTML5 / CSS3 / JS** | Fast SPA (no heavy bundlers), responsive SVG click analytics chart |
| **Testing** | **Pytest & TestClient** | 17 comprehensive unit/integration tests with in-memory Redis isolation |

---

## 🔄 User Flow

```
Landing / Auth (/auth/signup, /auth/login)
   │
   ▼
Dashboard (/)
   ├── 1. Primary Action: Paste long URL ──► Generate Base62 Short Code
   ├── 2. Live Stats: Total Links, Total Clicks, Active Links
   ├── 3. Link Management Table: Copy, Analytics, Delete
   │
   ▼
Click Analytics View
   ├── Total Clicks & Last Clicked Timestamp
   └── Responsive 7-Day Click Trend SVG Chart
```

---

## 📐 System Architecture

### 1. The Redis Cache-Aside Redirect Flow (`GET /{short_code}`)

Redirects account for **>95% of traffic** in URL shortener systems. ShortX optimizes this critical path using a Cache Hit/Miss pattern:

```
                    Incoming Visitor: GET /{short_code}
                                   │
                                   ▼
                       IP Rate Limit Validation
                        (100 req/min/IP via Redis)
                                   │
                                   ▼
                              Check Redis
                       KEY: "url:{short_code}"
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
               [Cache HIT]                   [Cache MISS]
                    │                             │
                    ▼                             ▼
            Retrieve original URL        Query PostgreSQL Database
                    │                             │
                    │                             ▼
                    │                     Write to Redis Cache
                    │                     (TTL: 86,400s / 24 hours)
                    │                             │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    Record Click Event (PostgreSQL)
                     (click_count + 1 & Click model)
                                   │
                                   ▼
                      HTTP 307 Temporary Redirect
                       Destination: Original URL
```

### 2. Database Schema

```
Users (users)                     URLs (urls)                        Clicks (clicks)
────────────────────              ───────────────────                ────────────────────
id (PK, Int, Auto)  ◄──────┐      id (PK, Int, Auto)  ◄──────┐       id (PK, Int, Auto)
email (String, Uniq)       │      user_id (FK, Users) ───────┘       url_id (FK, URLs) ──┘
password_hash (String)     └───── original_url (Text)                clicked_at (DateTime, Idx)
created_at (DateTime)             short_code (String, Uniq, Idx)     ip_address (String)
                                  click_count (Int, Def: 0)          user_agent (String)
                                  expires_at (DateTime, Null)
                                  created_at (DateTime)
```

---

## ⚡ Redis Engineering Decisions (SDE Interview Topics)

### 1. Sub-Millisecond Cache-Aside Redirects
- **Problem**: Querying disk-bound relational databases on every redirect creates database connection pool bottlenecks under heavy load.
- **Solution**: The first redirect for a link caches the `short_code -> original_url` mapping in Redis with a 24-hour TTL. All subsequent requests are resolved directly from memory in **< 5ms**.

### 2. Cache Invalidation Strategy
- **Problem**: When a user deletes a link, stale redirects might persist if the cache is not pruned.
- **Solution**: The `DELETE /urls/{id}` handler immediately executes `DEL url:{short_code}` in Redis inside `CacheService.delete_url()`, guaranteeing instant eviction.

### 3. Distributed Atomic Rate Limiter
- **Problem**: Open redirect and shortener endpoints are vulnerable to automated scraping, brute-force short-code guessing, and DoS attacks.
- **Solution**: ShortX implements a Redis-backed fixed-window rate limiter (`100 requests / minute / IP`) using atomic `INCR` operations and dynamic window expiration (`EXPIRE`). When exceeded, it immediately responds with `429 Too Many Requests` and a `Retry-After` header.

### 4. Resilient Fallback (Fault Tolerance)
- If the Redis connection drops, ShortX gracefully degrades without crashing, routing requests safely through the primary database and in-memory cache.

---

## 🔌 API Architecture

| Method | Endpoint | Description | Auth Required | Rate Limited |
|---|---|---|---|---|
| `POST` | `/auth/signup` | Create user account & return JWT | No | Yes (20/min) |
| `POST` | `/auth/login` | Authenticate credentials & return JWT | No | Yes (30/min) |
| `GET` | `/auth/me` | Get profile of authenticated user | **Bearer Token** | No |
| `POST` | `/urls` | Shorten a new long URL | **Bearer Token** | Yes (100/min) |
| `GET` | `/urls` | List all URLs belonging to user | **Bearer Token** | No |
| `GET` | `/urls/stats` | Dashboard metrics (links, clicks, active) | **Bearer Token** | No |
| `GET` | `/urls/{id}` | Inspect details for a specific URL | **Bearer Token** | No |
| `DELETE` | `/urls/{id}` | Delete URL & evict Redis cache entry | **Bearer Token** | No |
| `GET` | `/{short_code}` | Public redirect endpoint (Redis Hit/Miss) | No | Yes (100/min) |
| `GET` | `/urls/{id}/analytics` | 7-day click trend timeline & metrics | **Bearer Token** | No |
| `GET` | `/health` | Health check for API, DB, and Redis | No | No |

---

## 🧪 Testing & Validation

ShortX includes an automated test suite covering authentication, URL CRUD, protocol normalization, Redis hit/miss caching, cache invalidation, rate limiting, and analytics.

```bash
# Run tests with verbose output
pytest -v
```

```
tests/test_auth.py::test_signup_success PASSED                           [  5%]
tests/test_auth.py::test_signup_duplicate_email PASSED                   [ 11%]
tests/test_auth.py::test_login_success PASSED                            [ 17%]
tests/test_auth.py::test_login_wrong_password PASSED                     [ 23%]
tests/test_auth.py::test_get_current_user_me PASSED                      [ 29%]
tests/test_auth.py::test_get_current_user_unauthorized PASSED            [ 35%]
tests/test_cache.py::test_cache_hit_and_miss PASSED                      [ 41%]
tests/test_cache.py::test_redirect_populates_cache_on_miss PASSED        [ 47%]
tests/test_rate_limit.py::test_rate_limiter_blocks_excessive_requests PASSED [ 52%]
tests/test_redirect.py::test_redirect_to_original_url PASSED             [ 58%]
tests/test_redirect.py::test_redirect_nonexistent_returns_404 PASSED     [ 64%]
tests/test_redirect.py::test_url_analytics PASSED                        [ 70%]
tests/test_urls.py::test_create_short_url PASSED                         [ 76%]
tests/test_urls.py::test_create_url_normalizes_protocol PASSED           [ 82%]
tests/test_urls.py::test_list_urls PASSED                                [ 88%]
tests/test_urls.py::test_get_dashboard_stats PASSED                      [ 94%]
tests/test_urls.py::test_delete_url PASSED                               [100%]

======================== 17 passed in 7.76s =========================
```

---

## 🚀 Getting Started

### 🌐 Live Production Deployment
- **Web Application:** [https://shortx-95k9.onrender.com](https://shortx-95k9.onrender.com)
- **Interactive Swagger API Docs:** [https://shortx-95k9.onrender.com/docs](https://shortx-95k9.onrender.com/docs)
- **Health Check Endpoint:** [https://shortx-95k9.onrender.com/health](https://shortx-95k9.onrender.com/health)

---

### Method A: Docker Compose (Full Stack with PostgreSQL & Redis)

```bash
# 1. Clone the repository
git clone https://github.com/sanjayjujjuri28/ShortX.git
cd ShortX

# 2. Start all services in detached mode
docker compose up --build -d

# 3. Access the application:
# Web Dashboard: http://localhost:8000
# OpenAPI Docs:   http://localhost:8000/docs
```

### Method B: Local Python Development

```bash
# 1. Clone and enter directory
git clone https://github.com/sanjayjujjuri28/ShortX.git
cd ShortX

# 2. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```

---

## 📁 Repository Structure

```
ShortX/
├── app/
│   ├── config.py                 # Pydantic BaseSettings & env configs
│   ├── database.py               # Engine, sessionmaker, DB dependency
│   ├── redis.py                  # Redis client with graceful in-memory fallback
│   ├── security.py               # Bcrypt password hashing & JWT handling
│   ├── main.py                   # FastAPI app, middleware, routers, healthcheck
│   ├── models/                   # SQLAlchemy ORM Models
│   │   ├── user.py               # User table
│   │   ├── url.py                # URLs table
│   │   └── click.py              # Click analytics events
│   ├── schemas/                  # Pydantic V2 Schemas
│   │   ├── auth.py               # Signup, Login, Token schemas
│   │   ├── url.py                # URL creation & stats schemas
│   │   └── analytics.py          # Analytics timeline schemas
│   ├── services/                 # Layered Business Logic
│   │   ├── auth_service.py       # Authentication & user creation
│   │   ├── url_service.py        # Base62 code generation & CRUD
│   │   ├── cache_service.py      # Redis cache operations & eviction
│   │   └── rate_limit_service.py # Atomic Redis rate limiting
│   └── routers/                  # API Endpoint Controllers
│       ├── auth.py               # /auth endpoints
│       ├── urls.py               # /urls endpoints
│       ├── analytics.py          # /urls/{id}/analytics endpoints
│       └── redirect.py           # /{short_code} redirect engine
│
├── static/                       # Minimalist Web Frontend
│   ├── css/style.css             # Glassmorphic dark design system
│   ├── js/app.js                 # Vanilla JS SPA controller & SVG chart
│   └── index.html                # App layout (Auth, Dashboard, Analytics)
│
├── tests/                        # Pytest Test Suite
│   ├── conftest.py               # Test DB & Mock Redis fixtures
│   ├── test_auth.py              # Authentication test cases
│   ├── test_urls.py              # URL management test cases
│   ├── test_redirect.py          # Redirect & analytics test cases
│   ├── test_cache.py             # Redis hit/miss & eviction test cases
│   └── test_rate_limit.py        # Rate limiting test cases
│
├── Dockerfile                    # Production multi-stage Docker build
├── docker-compose.yml            # App + PostgreSQL 16 + Redis 7 compose
├── requirements.txt              # Pinned Python package dependencies
├── .env.example                  # Environment template
└── README.md                     # Documentation
```

---

## 🎯 Architectural Scope (Intentional Design Decisions)

To keep this project focused and optimal for Software Engineering interviews without bloated complexity, the following were intentionally excluded:
- ❌ Third-party OAuth (kept to clean JWT auth to focus on core API design)
- ❌ Microservice over-engineering (kept to a high-throughput modular monolith)
- ❌ Celery / Kafka queues (Redis directly handles caching & rate limiting; background tasks handle click analytics)
- ❌ Heavy frontend frameworks (Vanilla CSS + JS delivers sub-second load times and zero build-step overhead)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).