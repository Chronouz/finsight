"""
╔══════════════════════════════════════════════════════════════╗
║           FinSight AI — Expense Analyzer Engine              ║
║           Version  : 1.0.0                                   ║
║           Currency : IDR (Indonesian Rupiah)                 ║
║           Author   : FinSight Master                         ║
╚══════════════════════════════════════════════════════════════╝

Pipeline:
  1. Load simulated transaction JSON (sourced from FinSight Master analysis)
  2. Run category breakdown & summary statistics
  3. Anomaly / flag detection
  4. Console report output
  5. Export cleaned JSON to output/
"""

import json
import os
import sys
from datetime import datetime
from collections import defaultdict

# Ensure UTF-8 output on Windows terminals (PowerShell / cmd default to cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# 1. SIMULATED TRANSACTION DATA  (from FinSight Master session)
# ─────────────────────────────────────────────────────────────

RAW_PAYLOAD: dict = {
    "metadata": {
        "generated_by": "FinSight Master v1.0",
        "currency": "IDR",
        "total_transactions": 10,
        "pii_redacted": True,
        "statement_period": "November 2024",
    },
    "transactions": [
        {
            "id": 1,
            "original_text": "QRIS*TOKO KOPI TUKU JKT 12938",
            "normalized_merchant": "Toko Kopi Tuku",
            "category": "Food & Beverage",
            "amount": 45_000,
            "transaction_type": "debit",
            "flag": None,
        },
        {
            "id": 2,
            "original_text": "GRAB-FOOD/ORDER-8821",
            "normalized_merchant": "GrabFood",
            "category": "Food & Beverage",
            "amount": 78_500,
            "transaction_type": "debit",
            "flag": None,
        },
        {
            "id": 3,
            "original_text": "EDC BCA*INDOMARET ****0012 JKT",
            "normalized_merchant": "Indomaret",
            "category": "Shopping",
            "amount": 120_000,
            "transaction_type": "debit",
            "flag": None,
        },
        {
            "id": 4,
            "original_text": "TRF/IBK SALARY NOVEMBER 2024",
            "normalized_merchant": "Payroll - November 2024",
            "category": "Income",
            "amount": 8_500_000,
            "transaction_type": "credit",
            "flag": None,
        },
        {
            "id": 5,
            "original_text": "SHOPEE PAY*FASHION STORE",
            "normalized_merchant": "Shopee - Fashion Store",
            "category": "Shopping",
            "amount": 230_000,
            "transaction_type": "debit",
            "flag": None,
        },
        {
            "id": 6,
            "original_text": "DANA*GOPAY TOPUP",
            "normalized_merchant": "GoPay Top-Up",
            "category": "Transfer/Others",
            "amount": 500_000,
            "transaction_type": "debit",
            "flag": "POTENTIAL_DOUBLE_COUNT - reconcile against GoPay statement",
        },
        {
            "id": 7,
            "original_text": "PLN PREPAID TOKEN ****6789",
            "normalized_merchant": "PLN Prepaid Token",
            "category": "Utilities & Bills",
            "amount": 200_000,
            "transaction_type": "debit",
            "flag": "QUASI_SUBSCRIPTION - periodic top-up pattern",
        },
        {
            "id": 8,
            "original_text": "NETFLIX.COM/BILL",
            "normalized_merchant": "Netflix",
            "category": "Entertainment",
            "amount": 54_000,
            "transaction_type": "debit",
            "flag": "SUBSCRIPTION_DETECTED - monthly recurring charge",
        },
        {
            "id": 9,
            "original_text": "GRAB-BIKE/TRIP-4421",
            "normalized_merchant": "GrabBike",
            "category": "Transportation",
            "amount": 22_000,
            "transaction_type": "debit",
            "flag": None,
        },
        {
            "id": 10,
            "original_text": "QRIS*KLINIK SEHAT MANDIRI",
            "normalized_merchant": "Klinik Sehat Mandiri",
            "category": "Healthcare",
            "amount": 150_000,
            "transaction_type": "debit",
            "flag": None,
        },
    ],
}


# ─────────────────────────────────────────────────────────────
# 2. HELPER UTILITIES
# ─────────────────────────────────────────────────────────────

def fmt_idr(amount: int) -> str:
    """Format an integer as a human-readable IDR string."""
    return f"Rp {amount:>12,.0f}".replace(",", ".")


def separator(char: str = "─", width: int = 62) -> str:
    return char * width


def section_header(title: str) -> str:
    line = separator()
    return f"\n{line}\n  {title}\n{line}"


# ─────────────────────────────────────────────────────────────
# 3. CORE ANALYSIS ENGINE
# ─────────────────────────────────────────────────────────────

class FinSightAnalyzer:
    """
    Ingests a FinSight Master JSON payload, computes summary
    statistics, detects anomalies, and produces a console report
    plus an enriched JSON export.
    """

    EXPENSE_TYPES = {"debit"}
    INCOME_TYPES  = {"credit"}

    def __init__(self, payload: dict) -> None:
        self.metadata     = payload["metadata"]
        self.transactions = payload["transactions"]
        self._summary: dict = {}

    # ── 3a. Aggregations ──────────────────────────────────────

    def compute_summary(self) -> dict:
        """Compute totals, category breakdown, and flag lists."""
        total_income   = 0
        total_expenses = 0
        category_totals: dict[str, int] = defaultdict(int)
        flagged: list[dict] = []
        subscriptions: list[str] = []
        reconcile_required: list[str] = []

        for txn in self.transactions:
            amt  = txn["amount"]
            ttype = txn["transaction_type"]
            cat  = txn["category"]
            flag = txn.get("flag")

            if ttype in self.INCOME_TYPES:
                total_income += amt
            else:
                total_expenses += amt
                category_totals[cat] += amt

            if flag:
                flagged.append({"merchant": txn["normalized_merchant"], "flag": flag})
                if "SUBSCRIPTION" in flag.upper():
                    subscriptions.append(txn["normalized_merchant"])
                if "DOUBLE_COUNT" in flag.upper():
                    reconcile_required.append(txn["normalized_merchant"])

        top_category = max(category_totals, key=lambda k: category_totals[k])

        # Duplicate-amount detection (same amount, debit, different merchant)
        debit_amounts: dict[int, list[str]] = defaultdict(list)
        for txn in self.transactions:
            if txn["transaction_type"] == "debit":
                debit_amounts[txn["amount"]].append(txn["normalized_merchant"])

        duplicates = {
            amt: merchants
            for amt, merchants in debit_amounts.items()
            if len(merchants) > 1
        }

        self._summary = {
            "total_income":          total_income,
            "total_expenses":        total_expenses,
            "net_position":          total_income - total_expenses,
            "top_spending_category": top_category,
            "category_breakdown":    dict(category_totals),
            "flags": {
                "flagged_transactions":   flagged,
                "potential_subscriptions": subscriptions,
                "reconciliation_required": reconcile_required,
                "duplicate_amounts":       duplicates,
                "duplicates_detected":     bool(duplicates),
            },
        }
        return self._summary

    # ── 3b. Console Report ────────────────────────────────────

    def print_report(self) -> None:
        """Pretty-print the full analysis report to stdout."""
        s = self._summary
        if not s:
            s = self.compute_summary()

        print(section_header("SECTION 1 — METADATA & SECURITY SCAN"))
        print(f"  Generated by : {self.metadata['generated_by']}")
        print(f"  Period       : {self.metadata.get('statement_period', 'N/A')}")
        print(f"  Currency     : {self.metadata['currency']}")
        print(f"  Transactions : {self.metadata['total_transactions']}")
        print(f"  PII Redacted : {'✅ Yes' if self.metadata['pii_redacted'] else '❌ No'}")

        print(section_header("SECTION 2 — NORMALIZED EXPENSE LEDGER"))
        col = "{:<4} {:<28} {:<20} {:<16} {}"
        print(col.format("ID", "Merchant", "Category", "Amount (IDR)", "Type"))
        print(separator("·"))
        for t in self.transactions:
            print(col.format(
                t["id"],
                t["normalized_merchant"][:27],
                t["category"][:19],
                fmt_idr(t["amount"]),
                t["transaction_type"].upper(),
            ))

        print(section_header("SECTION 3 — FINANCIAL SUMMARY"))
        print(f"  {'Total Income':<26} {fmt_idr(s['total_income'])}")
        print(f"  {'Total Expenses':<26} {fmt_idr(s['total_expenses'])}")
        print(f"  {'Net Position':<26} {fmt_idr(s['net_position'])}")
        print(f"  {'Top Spending Category':<26} {s['top_spending_category']}")

        print(f"\n  {'Category Breakdown':}")
        print(f"  {separator('·', 46)}")
        for cat, total in sorted(s["category_breakdown"].items(),
                                  key=lambda x: x[1], reverse=True):
            bar_len = int((total / s["total_expenses"]) * 30) if s["total_expenses"] else 0
            bar = "█" * bar_len
            print(f"  {cat:<22} {fmt_idr(total)}  {bar}")

        print(section_header("SECTION 4 — ANOMALIES & FLAGS"))
        flags = s["flags"]

        if flags["potential_subscriptions"]:
            print("  ⚠️  Subscriptions detected:")
            for m in flags["potential_subscriptions"]:
                print(f"       • {m}")
        else:
            print("  ✅  No subscriptions detected.")

        if flags["reconciliation_required"]:
            print("\n  ⚠️  Reconciliation required:")
            for m in flags["reconciliation_required"]:
                print(f"       • {m}")

        if flags["duplicates_detected"]:
            print("\n  ⚠️  Duplicate amounts detected (same-day debit):")
            for amt, merchants in flags["duplicate_amounts"].items():
                print(f"       • {fmt_idr(amt)} → {', '.join(merchants)}")
        else:
            print("\n  ✅  No duplicate charge anomalies detected.")

        print(f"\n{separator()}\n")

    # ── 3c. JSON Export ───────────────────────────────────────

    def export_json(self, output_dir: str = "output") -> str:
        """
        Write enriched payload + computed summary to a timestamped
        JSON file in output_dir. Returns the output file path.
        """
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"finsight_analysis_{timestamp}.json"
        filepath  = os.path.join(output_dir, filename)

        export_payload = {
            "metadata":     self.metadata,
            "transactions": self.transactions,
            "summary":      self._summary or self.compute_summary(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, ensure_ascii=False, indent=2)

        return filepath


# ─────────────────────────────────────────────────────────────
# 4. ENTRY POINT
# ─────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "═" * 62)
    print("   FinSight AI — Expense Analyzer Engine  v1.0.0")
    print("═" * 62)

    analyzer = FinSightAnalyzer(RAW_PAYLOAD)
    analyzer.compute_summary()
    analyzer.print_report()

    export_path = analyzer.export_json(output_dir="output")
    print(f"  ✅ JSON export saved → {export_path}\n")


if __name__ == "__main__":
    main()
