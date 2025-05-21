## 📊 Finout Top Costs CLI

A Python CLI tool for querying Finout cost views, extracting the top N cost contributors, and optionally pushing the results or opening a filtered Finout report link.

---

### ✅ Features

- Query any Finout cost view via API
- Group by service, vendor, region, etc.
- Return top **N** cost items (default: 5)
- Optional total summary:
  - Total of top-N only
  - Full view total (from Finout's "Total" row)
- Output a Finout report link filtered to those top services
- Optional push to another API

---

### 🚀 Quick Start

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Add a \`.env\` file

Create a `.env` file like this:

```
FINOUT_CLIENT_ID=your-client-id
FINOUT_SECRET_KEY=your-secret-key
```

---

### 🧪 Example Usage

#### Basic (last month’s top 5 services)

```bash
python3 finout_top_costs.py \\
  --view-id YOUR_VIEW_ID \\
  --start-date 2024-04-01 \\
  --end-date 2024-04-30 \\
  --group-by service \\
  --include-total
```

#### Show top 10 vendors without date filters:

```bash
python3 finout_top_costs.py \\
  --view-id YOUR_VIEW_ID \\
  --omit-dates \\
  --group-by vendor \\
  --top-n 10 \\
  --include-total
```

#### Push the results to another API

```bash
python3 finout_top_costs.py \\
  --view-id YOUR_VIEW_ID \\
  --start-date 2024-04-01 \\
  --end-date 2024-04-30 \\
  --push-url https://your-api.com/receive \\
  --group-by service
```

---

### 🧾 Output Format

Example:

```json
{
  "action": "push_top_costs",
  "report_date": "2024-04-30",
  "source": "Finout",
  "top_costs": [
    { "service": "AmazonEC2", "amount_usd": 102.4, "percentage_of_total": 28.6 }
  ],
  "total": {
    "top_n": { "service": "Total (top 5)", "amount_usd": 357.0 },
    "full": { "service": "Total (view)", "amount_usd": 812.5 }
  },
  "metadata": {
    "currency": "USD",
    "extracted_by": "yourname@finout.io",
    "report_type": "cli_summary"
  }
}
```

---

### 🔗 Output URL

The tool prints a filtered Finout link like:

```
https://app.finout.io/app/total-cost?accountId=...&filters=...
```

---

### 🛠 CLI Flags Reference

| Flag              | Description |
|-------------------|-------------|
| ```--view-id```       | **(Required)** Finout view ID |
| ```--start-date```    | Start date (YYYY-MM-DD) |
| ```--end-date```      | End date (YYYY-MM-DD) |
| ```--omit-dates```    | Omit the date filter entirely |
| ```--group-by```      | Grouping key (\`service\`, \`vendor\`, \`region\`, etc.) |
| ```--top-n```         | How many cost items to return (default: 5) |
| ```--include-total``` | Include \`"total"\` object with both top-N and full view totals |
| ```--push-url```      | POST final payload to a URL |
