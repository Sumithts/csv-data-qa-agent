# Sample Run Transcript — CSV / Data Q&A Agent

Dataset: `data/sales_data.csv` (2000 rows)

## Q: What is the total revenue across all orders?

**Generated code:**
```python
result = round(df['revenue'].sum(), 2)
```

**Result:** `987999.41`

**Answer:** Sums the revenue column across every row.

---

## Q: Which region generated the highest total revenue?

**Generated code:**
```python
result = df.groupby('region')['revenue'].sum().idxmax()
```

**Result:** `North`

**Answer:** Groups by region, sums revenue per group, and picks the top one.

---

## Q: What is the average order profit for VIP customers?

**Generated code:**
```python
result = round(df[df['customer_segment'] == 'VIP']['profit'].mean(), 2)
```

**Result:** `203.34`

**Answer:** Filters to VIP orders and averages the profit column.

---

## Q: Which product category has the best profit margin (profit/revenue)?

**Generated code:**
```python
cat = df.groupby('category').agg(profit=('profit','sum'), revenue=('revenue','sum'))
cat['margin'] = cat['profit'] / cat['revenue']
result = cat['margin'].idxmax()
```

**Result:** `Books`

**Answer:** Aggregates profit and revenue per category, computes margin, picks the highest.

---

## Q: How many orders came from returning customers in the North region?

**Generated code:**
```python
result = len(df[(df['customer_segment'] == 'Returning') & (df['region'] == 'North')])
```

**Result:** `240`

**Answer:** Filters on both conditions and counts matching rows.

---

## Q: What was the total revenue in Q1 2025 (Jan-Mar 2025)?

**Generated code:**
```python
d = df.copy()
d['order_date'] = pd.to_datetime(d['order_date'])
mask = (d['order_date'] >= '2025-01-01') & (d['order_date'] <= '2025-03-31')
result = round(d.loc[mask, 'revenue'].sum(), 2)
```

**Result:** `168788.39`

**Answer:** Parses dates, filters to the Q1 2025 window, and sums revenue.

---

## Q: Which single product generated the highest total revenue?

**Generated code:**
```python
result = df.groupby('product')['revenue'].sum().idxmax()
```

**Result:** `Bluetooth Speaker`

**Answer:** Groups by product, sums revenue, and returns the top product.

---

## Q: What percentage of orders received a discount of 10% or more?

**Generated code:**
```python
result = round((df['discount_pct'] >= 10).mean() * 100, 2)
```

**Result:** `24.95`

**Answer:** Computes the share of rows where discount_pct is 10 or higher.

---

## Q: Compare average revenue per order between VIP and New customers.

**Generated code:**
```python
result = df[df['customer_segment'].isin(['VIP','New'])].groupby('customer_segment')['revenue'].mean().round(2).to_dict()
```

**Result:** `{'New': 527.18, 'VIP': 471.75}`

**Answer:** Filters to the two segments and averages revenue within each.

---

## Q: Which region had the fastest revenue growth from 2024 to 2025?

**Generated code:**
```python
d = df.copy()
d['order_date'] = pd.to_datetime(d['order_date'])
d['year'] = d['order_date'].dt.year
pivot = d[d['year'].isin([2024,2025])].groupby(['region','year'])['revenue'].sum().unstack()
pivot['growth_pct'] = (pivot[2025] - pivot[2024]) / pivot[2024] * 100
result = pivot['growth_pct'].idxmax()
```

**Result:** `East`

**Answer:** Splits revenue by region and year, computes YoY % growth per region, picks the max. (Note: 2025 data only covers Jan-Jun, so this compares partial-year to full-year — see Tradeoffs in the README.)

---

