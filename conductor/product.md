# Product Definition: NASCAR DFS Optimizer

## Initial Concept
DraftKings NASCAR DFS optimization using physics-compliant constraints, MCMC sampling, and a hybrid Native/Web architecture.

## Target Audience
- **DFS Players:** Serious competitors looking for an edge in DraftKings NASCAR contests.
- **Data Scientists & Analysts:** Professionals interested in race simulation, driver metaphysical modeling (skill, aggression), and structural race outcomes.

## Core Goals
- **Competitive Optimization:** Provide high-performance lineup generation that respects DraftKings rules and advanced predictive constraints.
- **Axiomatic Race Simulation:** Use physics-compliant constraints and MCMC (Markov Chain Monte Carlo) sampling to model race dynamics rather than just historical averages.
- **Hybrid Platform Experience:** Deliver a powerful, local-first macOS desktop experience coupled with a containerized web dashboard for accessibility and remote management.

## Key Features
- **MCMC Engine:** High-performance sampling using JAX and NumPyro, optimized for Apple Silicon and optional GPU offload.
- **Axiomatic Ontology:** A Neo4j graph database storing driver "metaphysical" properties (skill, shadow risk, aggression) and track-specific factors.
- **Native macOS Interface:** A fluid, tabbed PySide6/Qt6 application for managing race data, constraints, and jobs with full macOS HIG compliance.
- **Automated Infrastructure:** Data ingestion, model training, and job scheduling via Airflow pipelines and FastAPI backends.

## Design & Aesthetic
- **Platform Native:** The desktop application follows macOS Human Interface Guidelines (HIG) for a seamless system feel.
- **Data-Dense Web UI:** The web frontend prioritizes information density and clarity for complex race visualizations.
- **Brutalist Accents:** High-contrast neobrutalist elements (Neon Cyan, Yellow, Magenta) are used to highlight critical metrics and interactive states.

## Distribution & Deployment
- **Standalone macOS App:** Distributed as a signed `.app` bundle for high-performance, private, local processing.
- **Containerized Services:** Backend components (FastAPI, Neo4j, Redis) and the web frontend are managed via Docker for consistent deployment across environments.
