"""
Generates a realistic synthetic e-commerce sales dataset for the CSV Q&A Agent.
Run once: python generate_data.py -> writes sales_data.csv in this folder.
"""
import numpy as np
import pandas as pd

np.random.seed(42)

N = 2000

regions = ["North", "South", "East", "West"]
region_weights = [0.30, 0.22, 0.26, 0.22]

categories = {
    "Electronics": (150, 900),
    "Home & Kitchen": (20, 250),
    "Apparel": (10, 120),
    "Sports": (15, 200),
    "Books": (5, 45),
}

products = {
    "Electronics": ["Wireless Earbuds", "Smartwatch", "Bluetooth Speaker", "Laptop Stand", "4K Monitor"],
    "Home & Kitchen": ["Air Fryer", "Coffee Maker", "Blender", "Cookware Set", "Vacuum Cleaner"],
    "Apparel": ["Running Shoes", "Denim Jacket", "Cotton T-Shirt", "Wool Sweater", "Sneakers"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Cycling Helmet", "Football", "Resistance Bands"],
    "Books": ["Fiction Novel", "Self-Help Book", "Cookbook", "Biography", "Tech Manual"],
}

segments = ["New", "Returning", "VIP"]
segment_weights = [0.45, 0.40, 0.15]

dates = pd.date_range("2024-01-01", "2025-06-30", freq="D")

rows = []
for i in range(N):
    region = np.random.choice(regions, p=region_weights)
    category = np.random.choice(list(categories.keys()))
    product = np.random.choice(products[category])
    low, high = categories[category]
    unit_price = round(np.random.uniform(low, high), 2)
    quantity = np.random.randint(1, 6)
    discount_pct = np.random.choice([0, 0, 0, 5, 10, 15, 20], p=[0.35,0.15,0.1,0.15,0.15,0.05,0.05])
    date = np.random.choice(dates)
    segment = np.random.choice(segments, p=segment_weights)

    gross = unit_price * quantity
    revenue = round(gross * (1 - discount_pct / 100), 2)
    cost = round(gross * np.random.uniform(0.45, 0.65), 2)
    profit = round(revenue - cost, 2)

    rows.append({
        "order_id": f"ORD{10000+i}",
        "order_date": pd.Timestamp(date).strftime("%Y-%m-%d"),
        "region": region,
        "category": category,
        "product": product,
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_pct": discount_pct,
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "customer_segment": segment,
    })

df = pd.DataFrame(rows).sort_values("order_date").reset_index(drop=True)
df.to_csv("sales_data.csv", index=False)
print(f"Wrote {len(df)} rows to sales_data.csv")
print(df.head())
