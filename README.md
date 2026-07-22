# Agriverse FAMS (Farmer Advisory Management System)

FAMS is a sub-system of the Agriverse ecosystem designed to manage farm-level advisories, general broadcasts, and service catalog requests (e.g., tractor/drone bookings). 

This repository contains the complete prototype implementation, including a modern Next.js frontend and a fully integrated FastAPI backend with PostgreSQL, Redis, and an Nginx reverse proxy.

## Architecture & Tech Stack

This application is composed of several microservices coordinated via Docker Compose:

- **Frontend (`frontend/`)**: A Next.js (App Router) React application. It uses Vanilla CSS, features a highly responsive UI, and communicates with the backend via REST API calls.
- **Backend (`backend/`)**: A Python FastAPI application. It handles business logic, authentication (JWT), state machines for advisory workflows, and exposes REST endpoints.
- **Database (`db`)**: A PostgreSQL 15 database. Stores users, service centers, farms, advisories, and service requests using SQLAlchemy ORM.
- **Cache & Message Broker (`redis`)**: Redis 7. Used for computationally heavy API responses (like the leaderboard), high-performance request queuing, and caching external API data (like weather stubs).
- **Reverse Proxy (`nginx`)**: An Nginx container that acts as the entrypoint (port 80). It intelligently routes traffic to the `/api` prefix to the backend container, and all other traffic to the Next.js frontend container.

## Getting Started

### Prerequisites
- Docker and Docker Compose installed on your machine.

### 1. Setup Configuration
A `.env.example` file is provided at the root of the project. 
Copy it to create your local `.env` file:
```bash
cp .env.example .env
```
*(The defaults in `.env.example` are pre-configured to work out-of-the-box for local development).*

### 2. Build and Run the Application
To start the entire stack, run the following command in the root directory:

```bash
docker-compose up -d --build
```

**What happens when you run this?**
1. Docker builds the frontend and backend images.
2. The containers are started in the background (`-d`).
3. The database container spins up and provisions the `agriverse` database.
4. The `backend` container executes a startup script (`entrypoint.sh`). It runs Alembic/SQLAlchemy commands to create tables, and then executes `seed.py`. 
5. `seed.py` reads the mock data (`farms.json`) and populates the database with default Service Center Managers, Chief Agronomists, Farms, and initial mock Advisories.

### 3. Accessing the Application
Once the containers are running, simply navigate to:
**[http://localhost](http://localhost)**

You will see the FAMS login screen. You can log in using the seeded mock credentials (e.g., Manager or Chief Agronomist roles) simply by clicking the buttons (the UI passes the mock credentials to the backend automatically).

## Developer Guide: Managing Containers

If you are developing locally, you may need to restart specific services without taking down the entire stack.

**View all running containers:**
```bash
docker-compose ps
```

**View logs for a specific container (e.g., the backend):**
```bash
docker-compose logs -f backend
```

**Restarting a specific container:**
If you make changes to the frontend code, Next.js hot-reloading usually picks it up. But if you change package dependencies or want to force a restart:
```bash
docker-compose restart frontend
```

If you modify Python files in the backend, `uvicorn` is configured to auto-reload. However, if you change environment variables or the Dockerfile:
```bash
docker-compose up -d --build backend
```

**Shutting everything down:**
To stop the application and remove the containers (your database data will persist in the Docker volume):
```bash
docker-compose down
```

**Wiping the Database:**
If you want to start completely fresh and wipe the PostgreSQL volume so the seeder script runs from scratch on the next startup:
```bash
docker-compose down -v
```

## Directory Structure

```text
.
├── backend/                  # FastAPI Application
│   ├── models/               # SQLAlchemy Database Models
│   ├── schemas/              # Pydantic Schemas (API validation)
│   ├── routers/              # API Endpoints
│   ├── services/             # Business Logic & Workflow Rules
│   ├── seed.py               # Database Initialization Script
│   └── main.py               # Application Entrypoint
├── frontend/                 # Next.js Application
│   ├── src/app/              # App Router Pages (Dashboard, Advisories, etc.)
│   ├── src/components/       # Reusable UI Components
│   └── src/lib/              # API Client & State Management
├── docker-compose.yml        # Orchestration Config
├── nginx.conf                # Routing Configuration
├── .env.example              # Secret configurations template
└── README.md                 # You are here
```
