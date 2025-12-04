# Microservices Refactoring Plan for FPL Genius Bot

This document outlines the plan to refactor the FPL Genius Bot from a monolithic application into a more scalable and maintainable microservices architecture.

## 1. Current Architecture

The current system is a hybrid monolith. The core bot logic is a single, large Python script (`bot.py`) that orchestrates various services in-memory. This is tightly coupled with a client-server dashboard. While modular, the core bot logic is not independently scalable or easy to update without redeploying the entire application.

## 2. Proposed Architecture: A Service-Oriented Approach

We will break down the monolithic bot into a set of independent, collaborating microservices.

### 2.1. Service Boundaries

The following services will be created:

- **Orchestrator Service:**
  - **Responsibility:** The main entry point for the weekly workflow. It will not contain any business logic itself, but will be responsible for sending messages to the other services to trigger their work in the correct sequence. This will be the new, much slimmer version of `bot.py`.
  - **Technology:** Python.

- **FPL API Service:**
  - **Responsibility:** A dedicated service that acts as a proxy to the external FPL API. It will handle all authentication, session management, caching, and rate limiting. All other internal services that need FPL data will communicate with this service, not the FPL API directly.
  - **Technology:** Python, FastAPI.

- **ML Prediction Service:**
  - **Responsibility:** Manages the lifecycle of the machine learning model. It will expose endpoints for training the model and for getting predictions for players. It will handle model persistence internally.
  - **Technology:** Python, FastAPI.

- **Transfer Logic Service:**
  - **Responsibility:** Contains the core business logic for identifying transfer targets. It will receive the current squad and player data, and will return a list of recommended transfers.
  - **Technology:** Python, FastAPI.

### 2.2. Communication Strategy

To promote loose coupling and improve resilience, the services will communicate **asynchronously** using a message broker.

- **Technology:** We will use **RabbitMQ**. It is lightweight, easy to set up with Docker, and well-suited for the kind of chained-command workflow the bot uses.
- **Workflow Example:**
  1. The **Orchestrator** is triggered by the schedule.
  2. It sends a message: `get-fpl-data`.
  3. The **FPL API Service** consumes this message, fetches all the data, and once done, sends a new message: `fpl-data-ready` with the data (or a pointer to it).
  4. The **ML Prediction Service** and **Transfer Logic Service** might both consume the `fpl-data-ready` message to start their respective tasks.
  5. The **ML Prediction Service** trains the model and sends a `model-trained` message.
  6. The **Transfer Logic Service**, upon receiving both `fpl-data-ready` and `model-trained`, calculates the transfer recommendations and sends a `transfers-recommended` message.
  7. The **Orchestrator** consumes the `transfers-recommended` message and proceeds with executing the transfers (by calling the FPL API Service).

## 3. High-Level Refactoring Steps

1.  **[Done] Service Boundary Identification and Communication Strategy Proposal:** This document.
2.  **Containerization and Deployment Planning:** Update `docker-compose.yml` to include containers for RabbitMQ and the new services.
3.  **Implementation: Extract `fpl-api-service`:** Create the new service and refactor the Orchestrator to use it.
4.  **Implementation: Extract `ml-prediction-service`:** Create the new service and refactor the Orchestrator and other services to use it.
5.  **Implementation: Extract `transfer-logic-service`:** Create the new service.
6.  **Implementation: Refactor the Orchestrator:** Slim down the orchestrator to only be responsible for message passing and workflow control.

This phased approach will allow us to incrementally refactor the application without a "big bang" rewrite, ensuring the system remains functional throughout the process.
