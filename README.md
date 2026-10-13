# 💰 FinSight AI — Expense Analyzer Engine

A Python CLI tool that ingests structured financial transaction JSON
(produced by **FinSight Master**), computes summary statistics, detects
anomalies, and exports an enriched JSON report.

---

## 📁 Project Structure

```
finsight-ai/
├── expense-analyzer.py   ← Main analysis engine (entry point)
├── data/                 ← Drop raw JSON / CSV inputs here
├── output/               ← Auto-generated analysis exports (JSON)
├── reports/              ← Reserved for future PDF/HTML reports
├── requirements.txt      ← Python dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

**Requires:** Python 3.10+  — no third-party packages needed for the core engine.

```bash
# 1. Clone / navigate to the project folder
cd finsight-ai

# 2. Run the analyzer
python expense-analyzer.py
```

The script will:
1. Load the **simulated November 2024 transaction dataset** embedded in the file.
2. Print a full 4-section console report.
3. Export a timestamped JSON file to `output/`.

---

## 📊 Console Output Sections

| Section | Contents |
|---|---|
| **Section 1** | Metadata & PII redaction confirmation |
| **Section 2** | Normalized expense ledger table |
| **Section 3** | Totals, net position, category breakdown bar chart |
| **Section 4** | Anomalies: subscriptions, duplicates, reconciliation flags |

---

## 🗂️ JSON Export Schema

```json
{
  "metadata": { ... },
  "transactions": [ { "id", "original_text", "normalized_merchant",
                      "category", "amount", "transaction_type", "flag" } ],
  "summary": {
    "total_income": 8500000,
    "total_expenses": 1399500,
    "net_position": 7100500,
    "top_spending_category": "Shopping",
    "category_breakdown": { "Shopping": 350000, ... },
    "flags": {
      "potential_subscriptions": ["Netflix", "PLN Prepaid Token"],
      "reconciliation_required": ["GoPay Top-Up"],
      "duplicates_detected": false
    }
  }
}
```

---

## 🔧 Extending the Project

| Goal | How |
|---|---|
| Load from file | Replace `RAW_PAYLOAD` with `json.load(open("data/input.json"))` |
| Add CSV ingestion | Parse with `csv.DictReader`, map columns to transaction schema |
| Serve as REST API | Wrap `FinSightAnalyzer` in a FastAPI route |
| Generate charts | Pass `summary["category_breakdown"]` to `matplotlib` |

---

## 🔒 Security Notes

- Account/card numbers are masked with `****` before processing.
- No data is transmitted externally — fully offline pipeline.
- PII redaction status is confirmed in Section 1 of every report.

---

*Built with FinSight Master · IDR-native · Python 3.10+*
