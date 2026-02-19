# graphdb_learning_fraud
Project to learn more on Graph Database and Neo4j

## NexaCard Neo4j Setup -- Fake credit card company

### Prerequisites
- Docker Desktop running
- `.env` file in project root
- `scripts/generate_data.py` and `scripts/load_data.py` in place
- `data/source/` folder exists locally

---

### Step 1 — Build the Python image

```bash
docker compose build python
```

> Only needed once, or when you change `requirements.txt`.

---

### Step 2 — Start all containers

```bash
docker compose up -d
```

Expected output:
```
✔ Container neo4j             Started
✔ Container neo4j_scripts  Started
```

---

### Step 3 — Verify containers are running

```bash
docker compose ps
```

Both containers should show **Up** status:
```
NAME                STATUS
neo4j               Up
neo4j_scripts       Up
```

---

### Step 4 — Generate sample data

```bash
docker exec -it neo4j_scripts python generate_data.py
```

Expected output:
```
Generating NexaCard loyalty fraud dataset...

Saved to /scripts/data/source/nexacard_data.json

  Partners:           6
  Conversion Rates:   8
  Customers:          60
  NexaCard Accounts:  60
  Loyalty Accounts:   ~120
  Devices:            40
  Transfers (normal): ~250
  Transfers (fraud):  25

Fraud patterns injected:
  [1] ATO          — email hijack + immediate large drain
  [2] Velocity     — 12 transfers in 2 hours, same account
  [3] Promo abuse  — 8x hits on 2x promotional rate
  [4] Shared device — 4 customers, 1 device
```

---

### Step 5 — Confirm JSON file exists locally

```bash
ls ./data/source/
```

You should see:
```
nexacard_data.json
```

> This file is on your local machine because `./data/source` is bind mounted into the container.

---

### Step 6 — Load data into Neo4j

```bash
docker exec -it neo4j_scripts python load_data.py
```

Expected output:
```
Connecting to Neo4j at bolt://neo4j:7687...
Connected.

  Clearing existing data...
  Creating constraints...
  Loading 6 Partner nodes...
  Loading 8 ConversionRate nodes...
  Loading 60 Customer nodes...
  Loading 60 NexaAccount nodes...
  Loading ~120 LoyaltyAccount nodes...
  Loading 40 Device nodes...
  Loading ~275 PointsTransfer nodes...
  Creating relationships...

Load complete.
```

> **If you get a connection error** — Neo4j may still be initialising.
> Wait 15-20 seconds and try again.

```bash
# Wait and retry
sleep 15 && docker exec -it nexacard_scripts python load_data.py
```

---

### Step 7 — Verify in Neo4j Browser

Open **http://localhost:7474** in your browser.

Log in with credentials from your `.env` file:
```
Username: neo4j
Password: test_password
```

#### Useful starter queries

**Count all nodes by label:**
```cypher
MATCH (n) RETURN labels(n), count(n)
```

**See a sample of the graph:**
```cypher
MATCH (n) RETURN n LIMIT 50
```

**See a customer and all their connections:**
```cypher
MATCH (c:Customer)-[r]->(n)
RETURN c, r, n LIMIT 30
```

**See all transfers with partner:**
```cypher
MATCH (a:NexaAccount)-[:INITIATED_TRANSFER]->(t:PointsTransfer)-[:VIA_PARTNER]->(p:Partner)
RETURN a, t, p LIMIT 20
```

---

#### Fraud Detection Queries

**ATO — loyalty email changed vs customer email:**
```cypher
MATCH (cu:Customer)-[:OWNS_LOYALTY_ACCOUNT]->(la:LoyaltyAccount)
WHERE la.registered_email <> cu.email
RETURN cu.name, cu.email, la.loyalty_account_id, la.registered_email
```

**Velocity — accounts with 5+ transfers in same day:**
```cypher
MATCH (a:NexaAccount)-[:INITIATED_TRANSFER]->(t:PointsTransfer)
WITH a, count(t) AS transfer_count, sum(t.amex_points_debited) AS total_points
WHERE transfer_count >= 5
RETURN a.account_id, transfer_count, total_points
ORDER BY transfer_count DESC
```

**Promo abuse — accounts repeatedly using promotional rates:**
```cypher
MATCH (a:NexaAccount)-[:INITIATED_TRANSFER]->(t:PointsTransfer)-[:APPLIED_RATE]->(r:ConversionRate)
WHERE r.is_promotional = true
WITH a, count(t) AS promo_uses, sum(t.amex_points_debited) AS total_points
WHERE promo_uses > 3
RETURN a.account_id, promo_uses, total_points
ORDER BY promo_uses DESC
```

**Shared device — multiple customers using same device:**
```cypher
MATCH (t:PointsTransfer)-[:FROM_DEVICE]->(d:Device)
      <-[:USED_DEVICE]-(c:Customer)
WITH d, collect(DISTINCT c.name) AS customers, count(DISTINCT c) AS customer_count
WHERE customer_count > 1
RETURN d.device_id, customer_count, customers
ORDER BY customer_count DESC
```

---

#### Useful Docker Commands

```bash
# Stop all containers
docker compose down

# Stop and wipe Neo4j data (clean slate)
docker compose down -v

# View container logs
docker compose logs neo4j
docker compose logs python

# Shell into Python container
docker exec -it nexacard_scripts bash

# Restart just Neo4j
docker compose restart neo4j
```
