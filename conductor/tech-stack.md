# Technology Stack: NASCAR DFS Optimizer

## Core Languages & Runtimes
- **Python (3.11+):** Primary language for backend services, data science, optimization engine, and the native macOS desktop application.
- **TypeScript (5+):** Used for the web frontend to ensure type safety and modern development patterns.
- **Node.js:** Runtime for the Next.js web application and monorepo management.

## Application Frameworks
- **PySide6 (Qt6):** Powering the native macOS GUI, providing high-performance desktop components and system integration.
- **FastAPI:** High-performance REST API for the web-based microservices layer.
- **Next.js (14+):** React framework for the web dashboard, providing SSR/ISR capabilities for race data visualization.
- **Apache Airflow:** Orchestrates data ingestion pipelines, driver skill modeling, and periodic race updates.

## Data & Optimization
- **JAX & NumPyro:** The core of the "Axiomatic" optimizer, providing hardware-accelerated MCMC sampling and probabilistic programming.
- **Neo4j (5.x):** Graph database used to manage the driver/track ontology and metaphysical property relationships.
- **Polars & Pandas:** High-speed data manipulation and analysis for race statistics and history.
- **Redis:** Used for session caching, rate limiting, and managing background job queues.
- **SQLite:** Lightweight local persistence for the standalone macOS application's settings and race data.

## Infrastructure & Tooling
- **Docker & Docker Compose:** Containerization for backend, frontend, and database services ensuring parity between dev and prod.
- **Turbo (Turborepo):** Manages the monorepo structure, optimizing build tasks and dependency graphs.
- **UV:** Modern Python package manager used for extremely fast, reproducible environment management.
