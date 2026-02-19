from faker import Faker
import json
import random
from datetime import datetime, timedelta
import os

fake = Faker()
random.seed(42)
Faker.seed(42)

# --- Config ---
NUM_CUSTOMERS       = 60
NUM_TRANSACTIONS    = 250
OUTPUT_DIR          = "/scripts/data/source"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# --- Reference Data ---
PARTNERS = [
    {"partner_id": "PART_001", "name": "AuroraAir",    "category": "airline"},
    {"partner_id": "PART_002", "name": "ZenithWings",  "category": "airline"},
    {"partner_id": "PART_003", "name": "PolarJet",     "category": "airline"},
    {"partner_id": "PART_004", "name": "LuminaHotels", "category": "hotel"},
    {"partner_id": "PART_005", "name": "CrestResorts", "category": "hotel"},
    {"partner_id": "PART_006", "name": "AzureStays",   "category": "hotel"},
]

CONVERSION_RATES = [
    {"rate_id": "RATE_001", "partner_id": "PART_001", "ratio": 1.0,  "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
    {"rate_id": "RATE_002", "partner_id": "PART_001", "ratio": 2.0,  "is_promotional": True,  "valid_from": "2024-06-01", "valid_to": "2024-06-30"},
    {"rate_id": "RATE_003", "partner_id": "PART_002", "ratio": 0.75, "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
    {"rate_id": "RATE_004", "partner_id": "PART_003", "ratio": 1.0,  "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
    {"rate_id": "RATE_005", "partner_id": "PART_004", "ratio": 1.5,  "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
    {"rate_id": "RATE_006", "partner_id": "PART_004", "ratio": 3.0,  "is_promotional": True,  "valid_from": "2024-07-01", "valid_to": "2024-07-31"},
    {"rate_id": "RATE_007", "partner_id": "PART_005", "ratio": 1.25, "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
    {"rate_id": "RATE_008", "partner_id": "PART_006", "ratio": 1.0,  "is_promotional": False, "valid_from": "2024-01-01", "valid_to": "2024-12-31"},
]



DEVICE_TYPES = ["mobile", "desktop", "tablet"]
CHANNELS     = ["web", "mobile", "api", "phone"]
TIERS        = ["Standard", "Gold", "Platinum", "Centurion"]
KYC_STATUSES = ["verified", "pending", "failed"]

base_time = datetime(2024, 1, 1)



def generate_customers():
    customers = []
    for i in range(NUM_CUSTOMERS):
        customers.append({
            "customer_id":        f"CUST_{i:04d}",
            "name":               fake.name(),
            "email":              fake.email(),
            "phone":              fake.phone_number(),
            "dob":                fake.date_of_birth(minimum_age=18, maximum_age=70).isoformat(),
            "kyc_status":         random.choice(KYC_STATUSES),
            "account_created_at": (base_time - timedelta(days=random.randint(30, 1000))).isoformat(),
            "risk_score":         round(random.uniform(0, 1), 2)
        })
    return customers


def generate_nexa_accounts(customers):
    accounts = []
    for c in customers:
        accounts.append({
            "account_id":     f"NEXA_{c['customer_id']}",
            "customer_id":    c["customer_id"],
            "points_balance": random.randint(1000, 500000),
            "tier":           random.choice(TIERS),
            "status":         "active",
            "opened_at":      c["account_created_at"]
        })
    return accounts

def generate_loyalty_accounts(customers):
    loyalty_accounts = []
    la_id = 0
    customer_loyalty_map = {}  # customer_id -> list of loyalty_account_ids

    for c in customers:
        num_accounts = random.randint(1, 3)
        chosen_partners = random.sample(PARTNERS, num_accounts)
        customer_loyalty_map[c["customer_id"]] = []

        for partner in chosen_partners:
            la = {
                "loyalty_account_id": f"LA_{la_id:05d}",
                "customer_id":        c["customer_id"],
                "partner_id":         partner["partner_id"],
                "loyalty_number":     fake.bothify(text="??######??"),
                "status":             "active",
                "registered_email":   c["email"],
                "registered_phone":   c["phone"],
                "balance":            random.randint(0, 100000),
                "updated_at":         (base_time - timedelta(days=random.randint(1, 200))).isoformat()
            }
            loyalty_accounts.append(la)
            customer_loyalty_map[c["customer_id"]].append(la["loyalty_account_id"])
            la_id += 1

    return loyalty_accounts, customer_loyalty_map


def generate_devices(customers):
    devices = []
    device_customer_map = []
    num_devices = 40

    for i in range(num_devices):
        devices.append({
            "device_id":   f"DEV_{i:04d}",
            "ip_address":  fake.ipv4(),
            "device_type": random.choice(DEVICE_TYPES),
            "fingerprint": fake.md5(),
            "location":    fake.city()
        })

    # Assign 1-2 devices per customer normally
    for c in customers:
        assigned = random.sample(devices, random.randint(1, 2))
        for d in assigned:
            device_customer_map.append({
                "customer_id": c["customer_id"],
                "device_id":   d["device_id"]
            })

    return devices, device_customer_map


def generate_transfers(nexa_accounts, loyalty_accounts, devices, customer_loyalty_map):
    transfers = []
    tx_id = 0

    la_map = {la["loyalty_account_id"]: la for la in loyalty_accounts}

    for _ in range(NUM_TRANSACTIONS):
        nexa_acc = random.choice(nexa_accounts)
        cust_id  = nexa_acc["customer_id"]

        if not customer_loyalty_map.get(cust_id):
            continue

        la_id  = random.choice(customer_loyalty_map[cust_id])
        la     = la_map[la_id]
        rates_for_partner = [r for r in CONVERSION_RATES if r["partner_id"] == la["partner_id"]]
        rate   = random.choice(rates_for_partner if rates_for_partner else CONVERSION_RATES)
        device = random.choice(devices)
        points = random.randint(1000, 50000)
        ts     = base_time + timedelta(
                     days=random.randint(0, 364),
                     hours=random.randint(0, 23),
                     minutes=random.randint(0, 59)
                 )

        transfers.append({
            "transfer_id":             f"TX_{tx_id:05d}",
            "nexa_account_id":         nexa_acc["account_id"],
            "loyalty_account_id":      la_id,
            "partner_id":              la["partner_id"],
            "rate_id":                 rate["rate_id"],
            "amex_points_debited":     points,
            "partner_points_credited": round(points * rate["ratio"]),
            "conversion_ratio":        rate["ratio"],
            "is_promotional":          rate["is_promotional"],
            "timestamp":               ts.isoformat(),
            "status":                  "completed",
            "channel":                 random.choice(CHANNELS),
            "ip_address":              device["ip_address"],
            "device_id":               device["device_id"]
        })
        tx_id += 1

    return transfers, tx_id

def inject_fraud(transfers, loyalty_accounts, nexa_accounts, devices,
                 customer_loyalty_map, tx_id):

    fraud_transfers = []
    la_map = {la["loyalty_account_id"]: la for la in loyalty_accounts}

    # ------------------------------------------------------------------
    # Fraud 1: Account take over (hacked — loyalty account email changed, immediate large drain
    # ------------------------------------------------------------------
    ato_customer_id = nexa_accounts[0]["customer_id"]
    ato_la_id       = customer_loyalty_map[ato_customer_id][0]
    for la in loyalty_accounts:
        if la["loyalty_account_id"] == ato_la_id:
            la["registered_email"] = "madman_" + fake.email()  # changed email = ATO signal Random new email
            la["updated_at"]       = (base_time + timedelta(days=370)).isoformat() #Random timestamp

    fraud_transfers.append({
        "transfer_id":             f"TX_{tx_id:05d}",
        "nexa_account_id":         nexa_accounts[0]["account_id"],
        "loyalty_account_id":      ato_la_id,
        "partner_id":              la_map[ato_la_id]["partner_id"],
        "rate_id":                 "RATE_001",
        "amex_points_debited":     250000,
        "partner_points_credited": 250000,
        "conversion_ratio":        1.0,
        "is_promotional":          False,
        "timestamp":               (base_time + timedelta(days=370, hours=1)).isoformat(),
        "status":                  "completed",
        "channel":                 "web",
        "ip_address":              fake.ipv4(),
        "device_id":               devices[-1]["device_id"]  # unknown new device
    })
    tx_id += 1

    # ------------------------------------------------------------------
    # Fraud 2: Velocity abuse — 12 transfers from same account in 2 hours
    # ------------------------------------------------------------------
    velocity_account = nexa_accounts[5]
    velocity_la_id   = customer_loyalty_map[velocity_account["customer_id"]][0]
    velocity_device  = devices[3]
    t_vel            = base_time + timedelta(days=200, hours=10)

    for v in range(12):
        fraud_transfers.append({
            "transfer_id":             f"TX_{tx_id:05d}",
            "nexa_account_id":         velocity_account["account_id"],
            "loyalty_account_id":      velocity_la_id,
            "partner_id":              la_map[velocity_la_id]["partner_id"],
            "rate_id":                 "RATE_001",
            "amex_points_debited":     5000,
            "partner_points_credited": 5000,
            "conversion_ratio":        1.0,
            "is_promotional":          False,
            "timestamp":               (t_vel + timedelta(minutes=v * 10)).isoformat(),
            "status":                  "completed",
            "channel":                 "api",
            "ip_address":              velocity_device["ip_address"],
            "device_id":               velocity_device["device_id"]
        })
        tx_id += 1

    # ------------------------------------------------------------------
    # Fraud 3: Promo abuse — same account hits promotional rate 8 times
    # ------------------------------------------------------------------
    promo_account = nexa_accounts[10]
    promo_la_id   = customer_loyalty_map[promo_account["customer_id"]][0]
    for la in loyalty_accounts:
        if la["loyalty_account_id"] == promo_la_id:
            la["partner_id"] = "PART_001"

    for p in range(8):
        fraud_transfers.append({
            "transfer_id":             f"TX_{tx_id:05d}",
            "nexa_account_id":         promo_account["account_id"],
            "loyalty_account_id":      promo_la_id,
            "partner_id":              "PART_001",
            "rate_id":                 "RATE_002",  # promotional 2x rate
            "amex_points_debited":     30000,
            "partner_points_credited": 60000,
            "conversion_ratio":        2.0,
            "is_promotional":          True,
            "timestamp":               (base_time + timedelta(days=152 + p)).isoformat(),
            "status":                  "completed",
            "channel":                 "web",
            "ip_address":              fake.ipv4(),
            "device_id":               devices[5]["device_id"]
        })
        tx_id += 1

    # ------------------------------------------------------------------
    # Fraud 4: Shared device — 4 different customers using same device
    # ------------------------------------------------------------------
    shared_device   = devices[0]
    shared_accounts = nexa_accounts[20:24]

    for sc in shared_accounts:
        sc_la_id = customer_loyalty_map[sc["customer_id"]][0]
        fraud_transfers.append({
            "transfer_id":             f"TX_{tx_id:05d}",
            "nexa_account_id":         sc["account_id"],
            "loyalty_account_id":      sc_la_id,
            "partner_id":              la_map[sc_la_id]["partner_id"],
            "rate_id":                 "RATE_001",
            "amex_points_debited":     20000,
            "partner_points_credited": 20000,
            "conversion_ratio":        1.0,
            "is_promotional":          False,
            "timestamp":               (base_time + timedelta(days=300, hours=random.randint(0, 5))).isoformat(),
            "status":                  "completed",
            "channel":                 "mobile",
            "ip_address":              shared_device["ip_address"],
            "device_id":               shared_device["device_id"]
        })
        tx_id += 1

    return fraud_transfers


def main():
    print("Generating NexaCard loyalty fraud dataset...\n")

    customers                         = generate_customers()
    nexa_accounts                     = generate_nexa_accounts(customers)
    loyalty_accounts, cust_la_map     = generate_loyalty_accounts(customers)
    devices, device_cust_map          = generate_devices(customers)
    transfers, tx_id                  = generate_transfers(nexa_accounts, loyalty_accounts, devices, cust_la_map)
    fraud_transfers                   = inject_fraud(transfers, loyalty_accounts, nexa_accounts, devices, cust_la_map, tx_id)

    all_transfers = transfers + fraud_transfers

    data = {
        "partners":            PARTNERS,
        "conversion_rates":    CONVERSION_RATES,
        "customers":           customers,
        "nexa_accounts":       nexa_accounts,
        "loyalty_accounts":    loyalty_accounts,
        "devices":             devices,
        "device_customer_map": device_cust_map,
        "transfers":           all_transfers
    }

    out_path = os.path.join(OUTPUT_DIR, "nexacard_data.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved to {out_path}\n")
    print(f"  Partners:          {len(PARTNERS)}")
    print(f"  Conversion Rates:  {len(CONVERSION_RATES)}")
    print(f"  Customers:         {len(customers)}")
    print(f"  NexaCard Accounts: {len(nexa_accounts)}")
    print(f"  Loyalty Accounts:  {len(loyalty_accounts)}")
    print(f"  Devices:           {len(devices)}")
    print(f"  Transfers (normal):{len(transfers)}")
    print(f"  Transfers (fraud): {len(fraud_transfers)}")
    print(f"  Total Transfers:   {len(all_transfers)}")
    print("\n Same Fraud patterns injected:")
    print("  [1] Account take cover         — email hijack + immediate large drain")
    print("  [2] Velocity    — 12 transfers in 2 hours, same account")
    print("  [3] Promo abuse — 8x hits on 2x promotional rate")
    print("  [4] Shared device — 4 customers, 1 device")


if __name__ == "__main__":
    main()