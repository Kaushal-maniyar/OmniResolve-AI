# Customer 360 Neo4j Graph Database

Reproducible, script-driven **Neo4j Customer 360** graph database for Windows running as a native Windows service. This graph serves as the deterministic local graph foundation for OmniResolve AI.

---

## 1. Quick Start Guide

### Prerequisites
- Windows 10 / 11 (64-bit) with PowerShell Administrator access
- **Java JDK 21+** (e.g. Eclipse Temurin 21)
- Python 3.11+
- Pinned Neo4j version specified in [`neo4j.version`](file:///d:/hackathon/neo4j.version)

### First-Time Setup & Seeding

```powershell
# 1. Open PowerShell as Administrator
cd customer-360-neo4j

# 2. Setup virtual environment, configuration, initial password, service, and seed graph
.\scripts\setup.ps1

# 3. Verify graph invariants (59 nodes, 160 relationships, 0 violations)
.\scripts\verify.ps1

# 4. Test application Bolt connection
python app\examples\python_connection.py
```

---

## 2. Windows Service Management

Use the lifecycle scripts in `scripts/`:

```powershell
.\scripts\status-neo4j.ps1     # Check service status, listeners, and authentication
.\scripts\start-neo4j.ps1      # Start service and wait for Bolt port 7687
.\scripts\stop-neo4j.ps1       # Stop service
.\scripts\restart-neo4j.ps1    # Restart service
```

---

## 3. Endpoints & Credentials

- **Bolt URI:** `bolt://localhost:7687`
- **HTTP Browser:** `http://localhost:7474`
- **User:** `neo4j`
- **Password:** set in `.env` (`NEO4J_PASSWORD`)

---

## 4. Documentation

- [Windows Setup & Troubleshooting](docs/neo4j-windows-setup.md)
- [Graph Model & Schema Specification](docs/graph-model.md)
