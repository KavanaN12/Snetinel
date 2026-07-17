# Sentinel

Sentinel is a production-oriented security operations platform that combines a React frontend, a FastAPI backend, PostgreSQL, Redis, and background workers for discovery, attack path analysis, compliance, drift detection, audit logging, and RAG-driven insights.

## Overview

Sentinel provides a dashboard and operational workflows for:
- discovery and inventory
- attack path analysis
- compliance monitoring
- drift detection
- audit trails
- RAG-based explanations

## Architecture

The application is composed of:
- React frontend served by nginx
- FastAPI backend with modular APIs
- PostgreSQL for persistent data
- Redis for queueing and caching
- background worker for asynchronous processing

See [docs/architecture/architecture-diagram.md](docs/architecture/architecture-diagram.md).

## Features

- authentication and authorization
- role-based workspace access
- dashboard and findings views
- discovery workflows
- attack path analysis
- compliance and drift monitoring
- audit events
- RAG-based explanations

## Tech Stack

- Frontend: React, TypeScript, Vite, nginx
- Backend: FastAPI, Python, SQLAlchemy, Pydantic
- Data: PostgreSQL, Redis
- DevOps: Docker, Docker Compose, GitHub Actions, Render

## Folder Structure

- backend/: FastAPI application and tests
- frontend/: React application and nginx config
- infrastructure/: Docker Compose files
- docs/: architecture and project notes
- .github/workflows/: CI pipeline

## Docker Setup

### Development

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

### Production

```bash
docker compose -f infrastructure/docker-compose.prod.yml up --build
```

## Render Deployment

1. Create a PostgreSQL database and Redis instance on Render.
2. Deploy the backend as a web service using the Dockerfile in backend/.
3. Deploy the frontend as a web service using the Dockerfile in frontend/.
4. Set environment variables for the backend and frontend.
5. Configure CORS to include the frontend domain.

## Environment Variables

### Backend
- ENVIRONMENT
- DEBUG
- DATABASE_URL
- REDIS_URL
- JWT_SECRET_KEY
- JWT_ALGORITHM
- CORS_ALLOW_ORIGINS
- AWS_REGION
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_ENDPOINT_URL

### Frontend
- VITE_API_BASE_URL

## API Documentation

The backend exposes FastAPI endpoints under /api/v1 and health endpoints at /health, /readyz, and /livez.

## Screenshots

Add portfolio screenshots here before sharing the project publicly.

## Future Work

- enhance observability and monitoring
- add production secrets management
- expand automated integration coverage
- improve cloud discovery connectors

## License

MIT

## Contributing

Contributions are welcome. Please open an issue or pull request with a clear summary of the change.
