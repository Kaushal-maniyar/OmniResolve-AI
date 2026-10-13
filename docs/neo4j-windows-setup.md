# Neo4j Windows Setup & Operations Guide

## Installation Details

- **Target OS:** Windows 10/11 64-bit
- **Neo4j Version:** Pinned in `neo4j.version` (5.26.0)
- **Install Directory:** `C:\neo4j\neo4j-community-5.26.0`
- **Service Name:** `neo4j` (Windows Service)

## Prerequisites & Preflight Checks

1. **Java JDK 21**:
   Neo4j 5.x / 2026.x requires JDK 21. Verify with:
   ```powershell
   java -version
   ```

2. **PowerShell Elevation**:
   Service installation and startup require elevated Administrator rights.

## Service Commands

- **Install Service:** `bin\neo4j.bat windows-service install`
- **Uninstall Service:** `bin\neo4j.bat windows-service uninstall` (leaves data untouched)
- **Start Service:** `Start-Service -Name neo4j`
- **Stop Service:** `Stop-Service -Name neo4j`

## Managed Overrides Configuration (`config/neo4j.overrides.conf`)

`setup.ps1` maintains a managed block at the end of `conf/neo4j.conf`:

```properties
# >>> customer-360 managed block (do not edit by hand) >>>
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:7687
server.http.listen_address=127.0.0.1:7474
server.https.enabled=false
dbms.security.auth_enabled=true
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g
server.memory.pagecache.size=256m
# <<< customer-360 managed block <<<
```
