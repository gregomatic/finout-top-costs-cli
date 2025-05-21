import requests
import json
import argparse
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
import os
from urllib.parse import quote

# --- Load credentials from .env ---
load_dotenv()
FINOUT_CLIENT_ID = os.getenv("FINOUT_CLIENT_ID")
FINOUT_SECRET_KEY = os.getenv("FINOUT_SECRET_KEY")

if not FINOUT_CLIENT_ID or not FINOUT_SECRET_KEY:
    raise Exception("Missing FINOUT_CLIENT_ID or FINOUT_SECRET_KEY in .env")

def to_unix_millis(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def query_finout_costs(start_date, end_date, omit_dates=False, view_id=None, group_by=None):
    headers = {
        "x-finout-client-id": FINOUT_CLIENT_ID,
        "x-finout-secret-key": FINOUT_SECRET_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "viewId": view_id
    }
    if group_by:
        payload["groupBy"] = [group_by]
    if not omit_dates:
        payload["date"] = {
            "unixTimeMillSecondsStart": to_unix_millis(start_date),
            "unixTimeMillSecondsEnd": to_unix_millis(end_date)
        }

    print("\n🔍 Sending payload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        "https://app.finout.io/v1/cost/query-by-view",
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        raise Exception(f"Finout API Error: {response.status_code} - {response.text}")

    try:
        data = response.json()
        if isinstance(data, dict):
            if "results" in data:
                return data["results"]
            elif "data" in data:
                return data["data"]
        return data
    except ValueError:
        raise ValueError("Response was not valid JSON")

def summarize_top_costs(data, include_total=False, top_n=5):
    if isinstance(data, list):
        parsed = []
        for i, item in enumerate(data):
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except json.JSONDecodeError:
                    print(f"⚠️ Skipping invalid JSON item at index {i}")
                    continue
            if isinstance(item, dict):
                parsed.append(item)
        data = parsed

    print(f"\n📦 Parsed {len(data)} items from Finout API")

    cost_summary = defaultdict(float)
    full_total_cost = 0.0

    for item in data:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "Unknown")
        daily_costs = item.get("data", [])
        total_cost = sum(float(entry.get("cost", 0)) for entry in daily_costs)

        if name == "Total":
            full_total_cost = total_cost
            continue

        cost_summary[name] += total_cost

    # Extract top N and compute top-N total
    top = sorted(cost_summary.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_n_total = sum(amount for _, amount in top)

    if top_n_total == 0:
        print("\n⚠️ Total cost is 0 — no cost entries will be included.")
        return [], None

    results = [
        {
            "service": name,
            "amount_usd": round(amount, 2),
            "percentage_of_total": round((amount / top_n_total) * 100, 1)
        }
        for name, amount in top
    ]

    # Build total object with both top-N and full view total
    total_entry = None
    if include_total:
        total_entry = {
            "top_n": {
                "service": f"Total (top {top_n})",
                "amount_usd": round(top_n_total, 2)
            }
        }
        if full_total_cost > 0:
            total_entry["full"] = {
                "service": "Total (view)",
                "amount_usd": round(full_total_cost, 2)
            }

    return results, total_entry

def build_payload(top_list, report_date, total_entry=None):
    payload = {
        "action": "push_top_costs",
        "report_date": report_date,
        "source": "Finout",
        "top_costs": top_list,
        "metadata": {
            "currency": "USD",
            "extracted_by": "greg.ohare@finout.io",
            "report_type": "cli_summary"
        }
    }
    if total_entry:
        payload["total"] = total_entry
    return payload

def push_to_api(payload, url):
    if not payload["top_costs"]:
        print("\n🚫 No costs to push — skipping API call.")
        return 0, "Skipped push due to empty results"
    res = requests.post(url, json=payload)
    return res.status_code, res.text

def generate_filter_url(account_id, top_services):
    filter_obj = {
        "key": "parent_cloud_service",
        "type": "col",
        "operator": "oneOf",
        "value": top_services
    }
    encoded_filters = quote(json.dumps(filter_obj))
    return f"https://app.finout.io/app/total-cost?accountId={account_id}&filters={encoded_filters}"

def main():
    parser = argparse.ArgumentParser(description="Get top Finout costs and optionally push to external system")
    parser.add_argument("--start-date", required=False, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=False, help="End date (YYYY-MM-DD)")
    parser.add_argument("--push-url", help="Optional: URL to push the result")
    parser.add_argument("--group-by", help="Optional: override grouping of the view")
    parser.add_argument("--omit-dates", action="store_true", help="Omit date filter in API request")
    parser.add_argument("--view-id", required=True, help="Finout view ID to query")
    parser.add_argument("--include-total", action="store_true", help="Include total cost entry")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top cost items to return (default: 5)")

    args = parser.parse_args()

    if not args.omit_dates and (not args.start_date or not args.end_date):
        parser.error("--start-date and --end-date are required unless --omit-dates is used.")

    print(f"\n📅 Querying Finout from {args.start_date} to {args.end_date}")
    data = query_finout_costs(
        start_date=args.start_date,
        end_date=args.end_date,
        omit_dates=args.omit_dates,
        view_id=args.view_id,
        group_by=args.group_by
    )

    print("\n📊 Processing top cost services...")
    top_list, total_entry = summarize_top_costs(data, include_total=args.include_total, top_n=args.top_n)
    payload = build_payload(top_list, args.end_date or "N/A", total_entry=total_entry)

    print("\n✅ Top Cost Payload:")
    print(json.dumps(payload, indent=2))

    top_service_names = [entry["service"] for entry in top_list]
    report_url = generate_filter_url(account_id="e6ad4c08-9ecd-4592-be61-7a13ad456259", top_services=top_service_names)
    print("\n🔗 Finout filtered report URL:")
    print(report_url)

    if args.push_url:
        status, response = push_to_api(payload, args.push_url)
        if status:
            print("✅ Push status:", status)
            print("🔁 Response:", response)

if __name__ == "__main__":
    main()
