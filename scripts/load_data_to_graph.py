import json
import os
from neo4j import GraphDatabase

NEO4J_URL      = os.environ.get("NEO4J_URL", "Url not defined in env variables")
NEO4J_USER     = os.environ.get("NEO4J_USER", "Username not defined in env")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "Password not defined in env")
DATA_FILE      = "/scripts/data/source/nexacard_data.json"


def load_json():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def clear_db(session):
    print("  Clearing existing data...")
    session.run("MATCH (n) DETACH DELETE n")


def create_constraints(session):
    print("  Creating constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Partner)        REQUIRE p.partner_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (r:ConversionRate) REQUIRE r.rate_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Customer)       REQUIRE c.customer_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:NexaAccount)    REQUIRE a.account_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (l:LoyaltyAccount) REQUIRE l.loyalty_account_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Device)         REQUIRE d.device_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:PointsTransfer) REQUIRE t.transfer_id IS UNIQUE",
    ]
    for c in constraints:
        session.run(c)


# -------------------------------------------
# Node loaders
# -------------------------------------------

def load_partners(session, partners):
    print(f"  Loading {len(partners)} Partner nodes...")
    for p in partners:
        session.run("""
            MERGE (p:Partner {partner_id: $partner_id})
            SET p.name     = $name,
                p.category = $category,
                p.status   = 'active'
        """, **p)


def load_conversion_rates(session, rates):
    print(f"  Loading {len(rates)} ConversionRate nodes...")
    for r in rates:
        session.run("""
            MERGE (r:ConversionRate {rate_id: $rate_id})
            SET r.ratio            = $ratio,
                r.is_promotional   = $is_promotional,
                r.valid_from       = $valid_from,
                r.valid_to         = $valid_to,
                r.partner_id       = $partner_id
        """, **r)


def load_customers(session, customers):
    print(f"  Loading {len(customers)} Customer nodes...")
    for c in customers:
        session.run("""
            MERGE (c:Customer {customer_id: $customer_id})
            SET c.name               = $name,
                c.email              = $email,
                c.phone              = $phone,
                c.dob                = $dob,
                c.kyc_status         = $kyc_status,
                c.account_created_at = $account_created_at,
                c.risk_score         = $risk_score
        """, **c)


def load_nexa_accounts(session, accounts):
    print(f"  Loading {len(accounts)} NexaAccount nodes...")
    for a in accounts:
        session.run("""
            MERGE (a:NexaAccount {account_id: $account_id})
            SET a.points_balance = $points_balance,
                a.tier           = $tier,
                a.status         = $status,
                a.opened_at      = $opened_at
        """, **a)


def load_loyalty_accounts(session, accounts):
    print(f"  Loading {len(accounts)} LoyaltyAccount nodes...")
    for la in accounts:
        session.run("""
            MERGE (la:LoyaltyAccount {loyalty_account_id: $loyalty_account_id})
            SET la.loyalty_number    = $loyalty_number,
                la.status            = $status,
                la.registered_email  = $registered_email,
                la.registered_phone  = $registered_phone,
                la.balance           = $balance,
                la.updated_at        = $updated_at,
                la.partner_id        = $partner_id
        """, **la)


def load_devices(session, devices):
    print(f"  Loading {len(devices)} Device nodes...")
    for d in devices:
        session.run("""
            MERGE (d:Device {device_id: $device_id})
            SET d.ip_address  = $ip_address,
                d.device_type = $device_type,
                d.fingerprint = $fingerprint,
                d.location    = $location
        """, **d)


def load_transfers(session, transfers):
    print(f"  Loading {len(transfers)} PointsTransfer nodes...")
    for t in transfers:
        session.run("""
            MERGE (t:PointsTransfer {transfer_id: $transfer_id})
            SET t.points_debited     = $points_debited,
                t.partner_points_credited = $partner_points_credited,
                t.conversion_ratio        = $conversion_ratio,
                t.is_promotional          = $is_promotional,
                t.timestamp               = $timestamp,
                t.status                  = $status,
                t.channel                 = $channel,
                t.ip_address              = $ip_address
        """, **t)


# -------------------------------------------
# Relationship loaders
# -------------------------------------------

def load_relationships(session, data):
    print("  Creating relationships...")

    # (Customer)-[:HAS_NEXA_ACCOUNT]->(NexaAccount)
    for a in data["nexa_accounts"]:
        session.run("""
            MATCH (c:Customer   {customer_id: $customer_id})
            MATCH (a:NexaAccount {account_id: $account_id})
            MERGE (c)-[:HAS_NEXA_ACCOUNT]->(a)
        """, customer_id=a["customer_id"], account_id=a["account_id"])

    # (Customer)-[:OWNS_LOYALTY_ACCOUNT]->(LoyaltyAccount)
    for la in data["loyalty_accounts"]:
        session.run("""
            MATCH (c:Customer      {customer_id: $customer_id})
            MATCH (la:LoyaltyAccount {loyalty_account_id: $loyalty_account_id})
            MERGE (c)-[:OWNS_LOYALTY_ACCOUNT]->(la)
        """, customer_id=la["customer_id"], loyalty_account_id=la["loyalty_account_id"])

    # (LoyaltyAccount)-[:BELONGS_TO_PARTNER]->(Partner)
    for la in data["loyalty_accounts"]:
        session.run("""
            MATCH (la:LoyaltyAccount {loyalty_account_id: $loyalty_account_id})
            MATCH (p:Partner          {partner_id: $partner_id})
            MERGE (la)-[:BELONGS_TO_PARTNER]->(p)
        """, loyalty_account_id=la["loyalty_account_id"], partner_id=la["partner_id"])

    # (ConversionRate)-[:RATE_FOR]->(Partner)
    for r in data["conversion_rates"]:
        session.run("""
            MATCH (r:ConversionRate {rate_id: $rate_id})
            MATCH (p:Partner        {partner_id: $partner_id})
            MERGE (r)-[:RATE_FOR]->(p)
        """, rate_id=r["rate_id"], partner_id=r["partner_id"])

    # (Customer)-[:USED_DEVICE]->(Device)
    for dc in data["device_customer_map"]:
        session.run("""
            MATCH (c:Customer {customer_id: $customer_id})
            MATCH (d:Device   {device_id: $device_id})
            MERGE (c)-[:USED_DEVICE]->(d)
        """, **dc)

    # Transfer relationships
    for t in data["transfers"]:
        # (NexaAccount)-[:INITIATED_TRANSFER]->(PointsTransfer)
        session.run("""
            MATCH (a:NexaAccount    {account_id: $nexa_account_id})
            MATCH (t:PointsTransfer {transfer_id: $transfer_id})
            MERGE (a)-[:INITIATED_TRANSFER]->(t)
        """, nexa_account_id=t["nexa_account_id"], transfer_id=t["transfer_id"])

        # (PointsTransfer)-[:TRANSFERRED_TO]->(LoyaltyAccount)
        session.run("""
            MATCH (t:PointsTransfer  {transfer_id: $transfer_id})
            MATCH (la:LoyaltyAccount {loyalty_account_id: $loyalty_account_id})
            MERGE (t)-[:TRANSFERRED_TO]->(la)
        """, transfer_id=t["transfer_id"], loyalty_account_id=t["loyalty_account_id"])

        # (PointsTransfer)-[:VIA_PARTNER]->(Partner)
        session.run("""
            MATCH (t:PointsTransfer {transfer_id: $transfer_id})
            MATCH (p:Partner        {partner_id: $partner_id})
            MERGE (t)-[:VIA_PARTNER]->(p)
        """, transfer_id=t["transfer_id"], partner_id=t["partner_id"])

        # (PointsTransfer)-[:APPLIED_RATE]->(ConversionRate)
        session.run("""
            MATCH (t:PointsTransfer {transfer_id: $transfer_id})
            MATCH (r:ConversionRate {rate_id: $rate_id})
            MERGE (t)-[:APPLIED_RATE]->(r)
        """, transfer_id=t["transfer_id"], rate_id=t["rate_id"])

        # (PointsTransfer)-[:FROM_DEVICE]->(Device)
        session.run("""
            MATCH (t:PointsTransfer {transfer_id: $transfer_id})
            MATCH (d:Device         {device_id: $device_id})
            MERGE (t)-[:FROM_DEVICE]->(d)
        """, transfer_id=t["transfer_id"], device_id=t["device_id"])


# -------------------------------------------
# Main
# -------------------------------------------

def main():
    print(f"\nConnecting to Neo4j at {NEO4J_URL}...")
    driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        print("Connected.\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Is Neo4j running? Try again in a few seconds.")
        return

    data = load_json()

    with driver.session() as session:
        clear_db(session)
        create_constraints(session)

        # Nodes
        load_partners(session, data["partners"])
        load_conversion_rates(session, data["conversion_rates"])
        load_customers(session, data["customers"])
        load_nexa_accounts(session, data["nexa_accounts"])
        load_loyalty_accounts(session, data["loyalty_accounts"])
        load_devices(session, data["devices"])
        load_transfers(session, data["transfers"])

        # Relationships
        load_relationships(session, data)

    driver.close()

    print("\nLoad complete. Summary:")
    print(f"  Partners:          {len(data['partners'])}")
    print(f"  Conversion Rates:  {len(data['conversion_rates'])}")
    print(f"  Customers:         {len(data['customers'])}")
    print(f"  NexaCard Accounts: {len(data['nexa_accounts'])}")
    print(f"  Loyalty Accounts:  {len(data['loyalty_accounts'])}")
    print(f"  Devices:           {len(data['devices'])}")
    print(f"  Transfers:         {len(data['transfers'])}")
    print("\nOpen Neo4j browser at http://localhost:7474")
    print("Run this to see the full graph:")
    print("  MATCH (n) RETURN n LIMIT 100")


if __name__ == "__main__":
    main()