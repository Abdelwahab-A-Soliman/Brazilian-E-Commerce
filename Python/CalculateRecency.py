import pandas as pd
import time

# ==========================
# Read Orders CSV
# ==========================
orders = pd.read_csv(
    "olist_orders_dataset.csv",
    parse_dates=["order_purchase_timestamp"]
)

# Optional: Keep only delivered orders
# orders = orders[orders["order_status"] == "delivered"]

orders = orders[["customer_id", "order_purchase_timestamp"]].dropna()
orders = orders.sort_values(["customer_id", "order_purchase_timestamp"])

# ==========================
# Fixed Month Range
# ==========================

months = pd.date_range(
    start="2017-01-01",
    end="2018-12-01",
    freq="MS"   # Month Start
)

customers = orders["customer_id"].unique()

customer_month = (
    pd.MultiIndex.from_product(
        [customers, months],
        names=["customer_id", "month_start"]
    )
    .to_frame(index=False)
)

# ==========================
# Calculate Recency (with progress reporting)
# ==========================

# Optional: use tqdm if available for a nicer progress bar
try:
    from tqdm import tqdm
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False

results = []

total_customers = len(customers)
start_time = time.time()

if _HAS_TQDM:
    customer_iter = tqdm(orders.groupby("customer_id"), total=total_customers, desc="Customers")
else:
    customer_iter = orders.groupby("customer_id")

for idx, (customer, group) in enumerate(customer_iter, start=1):

    purchases = (
        group[["order_purchase_timestamp"]]
        .rename(columns={"order_purchase_timestamp": "last_purchase_date"})
        .sort_values("last_purchase_date")
    )

    cust_months = customer_month[
        customer_month["customer_id"] == customer
    ].sort_values("month_start")

    merged = pd.merge_asof(
        cust_months,
        purchases,
        left_on="month_start",
        right_on="last_purchase_date",
        direction="backward",
        allow_exact_matches=False
    )

    merged["RECENCY_DAYS"] = (
        merged["month_start"] - merged["last_purchase_date"]
    ).dt.days

    results.append(merged)

    # When tqdm isn't available, print periodic progress + ETA
    if not _HAS_TQDM and (idx % 100 == 0 or idx == total_customers):
        elapsed = time.time() - start_time
        remaining = total_customers - idx
        eta = (elapsed / idx) * remaining if idx else 0
        print(f"Processed {idx}/{total_customers} customers - elapsed: {elapsed:.1f}s - ETA: {eta:.1f}s")

recency = pd.concat(results, ignore_index=True)

# ==========================
# Final Output
# ==========================

recency["DATEKEY"] = recency["month_start"].dt.strftime("%Y%m").astype(int)

recency = recency[
    [
        "customer_id",
        "DATEKEY",
        "RECENCY_DAYS",
        "last_purchase_date"
    ]
].rename(columns={
    "last_purchase_date": "LAST_PURCHASE_DATE"
})

recency.to_csv("customer_monthly_recency.csv", index=False)

print(recency.head(20))