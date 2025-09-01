# PRD: PostgreSQL Database Support
This document outlines the requirements for integrating PostgreSQL as a primary database backend for MyWebIntelligence, transitioning from a development plan to a full-fledged Product Requirements Document (PRD).

## 1. Introduction & Vision

### 1.1. Problem Statement
MyWebIntelligence currently relies exclusively on SQLite, which is ideal for single-user, portable use cases. However, it presents significant limitations for users who need to manage larger datasets, support concurrent operations, or collaborate in a team environment. The lack of a robust, scalable database backend is a key barrier to adoption for power users, research teams, and any production-level deployment.

### 1.2. Vision & Goal
The goal is to evolve MyWebIntelligence into a more scalable and collaborative platform by adding native support for PostgreSQL. This will empower users to handle enterprise-grade workloads and integrate the tool into larger data ecosystems. The implementation will be seamless, configurable, and will not compromise existing SQLite functionality.

### 1.3. Target Audience
*   **Power Users & Data Scientists:** Individuals managing web data archives exceeding the practical limits of SQLite, requiring advanced SQL querying capabilities.
*   **Research Teams:** Collaborative groups needing a centralized, shared database for their web intelligence projects with role-based access and concurrent operations.
*   **System Integrators:** Developers embedding MyWebIntelligence into larger data processing pipelines that already leverage PostgreSQL.

### 1.4. User Stories
*   **As a Data Scientist,** I want to store and analyze millions of web pages so that I can conduct large-scale trend analysis without performance degradation.
*   **As a Research Lead,** I want my team to connect to a single, shared PostgreSQL database so that we can collaborate on the same dataset in real-time.
*   **As a Developer,** I want to configure the application to use our existing PostgreSQL infrastructure so that I can easily integrate MyWebIntelligence into our standard deployment environment.

---

## 2. Feature Scope

### 2.1. In Scope
*   Full support for PostgreSQL as a database backend, configurable via settings.
*   Feature parity between the SQLite and PostgreSQL implementations.
*   A CLI command to initialize the database schema in PostgreSQL.
*   Official support for `psycopg2-binary` as the database driver.
*   Documentation on configuring and managing a PostgreSQL connection.
*   A data migration utility to transfer data from SQLite to PostgreSQL.

### 2.2. Out of Scope
*   Support for other database engines (e.g., MySQL, Oracle).
*   Automatic, real-time database synchronization between SQLite and PostgreSQL.
*   A graphical user interface (GUI) for managing database connections or migrations.
*   Hosting or managing the PostgreSQL server instance for the user.

---

## 3. Requirements

### 3.1. Functional Requirements
*   **Database Configuration:** Users must be able to specify the database engine (`sqlite` or `postgres`) and connection details (host, port, user, password, dbname) in `settings.py`.
*   **ORM Compatibility:** The Peewee ORM must function correctly with the `peewee.PostgresqlDatabase` adapter. All existing model definitions and queries must work without modification.
*   **CLI Integration:** All `mywi` CLI commands must operate seamlessly on a PostgreSQL database.
*   **Data Migration:** A standalone script or CLI command (`mywi db migrate`) must be provided to export data from an SQLite database and import it into a PostgreSQL database.

### 3.2. Non-Functional Requirements
*   **Performance:** Application performance (crawling, analysis, querying) with PostgreSQL should be equal to or better than with SQLite, especially on large datasets.
*   **Security:** Connections to PostgreSQL must support SSL/TLS encryption. Credentials must not be hardcoded and should be manageable via environment variables or a secure configuration file (`.env`).
*   **Scalability:** The system must be able to handle database sizes and concurrent connection loads typical of a small-to-medium enterprise environment.
*   **Reliability:** The database connection logic must include error handling and retry mechanisms for transient network issues.

---

## 4. Architecture & Design

### 4.1. Database Abstraction
A factory function, `get_database()`, will be implemented in `mwi/model.py`. This function will read the configuration from `settings.py` and return the appropriate Peewee `Database` instance (`SqliteDatabase` or `PostgresqlDatabase`). All models will be bound to this dynamic database instance.

### 4.2. Configuration
The `settings.py` file will be the primary source of configuration.

```python
# settings.py
DB_ENGINE = "sqlite"  # or "postgres"

# PostgreSQL Connection Details
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "mywi"
DB_USER = "mywi_user"
DB_PASSWORD = "your_secure_password" # Load from env var in production
```

### 4.3. Data Migration
The migration tool will be built using `playhouse.migrate`. It will follow a three-step process:
1.  Connect to the source SQLite database.
2.  Extract data, transforming types where necessary (e.g., `DATETIME` fields).
3.  Connect to the target PostgreSQL database and load the data, validating counts and constraints.

---

## 5. Implementation Plan (Milestones)

### Milestone 1: Core Backend Integration
*   **Task 1:** Add `psycopg2-binary` to `requirements.txt`.
*   **Task 2:** Implement the `get_database()` factory in `mwi/model.py`.
*   **Task 3:** Refactor the application to use the dynamic database connection.
*   **Task 4:** Manually test core functionalities (e.g., model creation) against a local PostgreSQL instance.

### Milestone 2: CLI & Configuration
*   **Task 1:** Update `settings.py` with the new PostgreSQL configuration variables.
*   **Task 2:** Ensure all CLI commands function correctly when pointed to PostgreSQL.
*   **Task 3:** Add a `mywi db setup` command to create tables in the configured database.

### Milestone 3: Data Migration Tooling
*   **Task 1:** Develop the `sqlite-to-postgres` migration script.
*   **Task 2:** Add a `mywi db migrate` command to expose this functionality.
*   **Task 3:** Write clear documentation for the migration process.

### Milestone 4: Testing & CI/CD
*   **Task 1:** Parameterize the pytest suite to run all relevant tests against both SQLite and PostgreSQL.
*   **Task 2:** Create a GitHub Actions workflow matrix to automate testing for both database engines in the CI pipeline.
*   **Task 3:** Conduct performance benchmarks for key operations.

---

## 6. Testing & Validation
*   **Unit Tests:** All model-layer tests must pass on both SQLite and PostgreSQL.
*   **Integration Tests:** The full CLI command suite will be tested against a live PostgreSQL database.
*   **Migration Tests:** The migration script will be tested with varied datasets, including edge cases (empty tables, special characters).

---

## 7. Deployment & Rollout
1.  **Beta Release:** The feature will first be released behind a feature flag or as an advanced configuration option for community testing.
2.  **General Availability:** After a successful beta period, PostgreSQL support will be officially documented as a standard feature. The default engine will remain SQLite to ensure backward compatibility for existing users.

---

## 8. Risks & Mitigation
*   **Risk:** ORM queries that use SQLite-specific functions may fail.
    *   **Mitigation:** Systematically review all raw SQL queries and Peewee extensions in use. Replace them with database-agnostic equivalents.
*   **Risk:** Data type inconsistencies during migration could lead to data loss.
    *   **Mitigation:** Implement a validation step in the migration script that compares row counts and checksums before finalizing the migration.

---

## 9. Success Metrics
*   **Adoption:** At least 10% of new installations/deployments are configured to use PostgreSQL within 6 months of release.
*   **Stability:** Fewer than 5 critical bugs related to the PostgreSQL integration are reported in the first 3 months.
*   **CI/CD:** The CI pipeline successfully and consistently runs all tests against both database backends.
*   **Documentation:** The documentation for PostgreSQL setup and migration is clear and receives positive community feedback.

---

## 10. Future Considerations
*   **Other Database Backends:** A successful implementation could create a pattern for supporting other databases like MySQL or MariaDB in the future.
*   **Read Replicas:** For very large-scale deployments, explore supporting PostgreSQL read replicas for query-intensive operations.