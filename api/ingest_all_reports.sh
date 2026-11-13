#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$REPO_ROOT/data/sources"
PYTHON="$SCRIPT_DIR/FIAenv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Python environment not found: $PYTHON" >&2
  echo "Create it first with: python3 -m venv $SCRIPT_DIR/FIAenv" >&2
  exit 1
fi

if [[ ! -d "$REPORT_DIR" ]]; then
  echo "Report directory not found: $REPORT_DIR" >&2
  exit 1
fi

cd "$SCRIPT_DIR"

ingest_report() {
  local ticker="$1"
  local filename="$2"
  local source_url="$3"
  local path="$REPORT_DIR/$filename"

  if [[ ! -f "$path" ]]; then
    echo "Missing report for $ticker: $path" >&2
    exit 1
  fi

  echo "Ingesting $ticker: $filename"
  PYTHONPATH=. "$PYTHON" ingest_documents.py \
    --ticker "$ticker" \
    --annual-report "$path" \
    --annual-report-url "$source_url" \
    --provenance verified
}

ingest_report "RELIANCE" \
  "RELIANCE-FY2025-annual-report.pdf" \
  "https://www.ril.com/ar2024-25/pdf/RIL-IAR-2025.pdf"

ingest_report "TCS" \
  "TCS-FY2026-annual-report.pdf" \
  "https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2025-26/ar/annual-report-2025-2026.pdf"

ingest_report "INFY" \
  "INFY-FY2026-annual-report.pdf" \
  "https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-26.pdf"

ingest_report "HDFCBANK" \
  "HDFCBANK-FY2025-annual-report.pdf" \
  "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/annual-reports/2024-25/HDFC_Bank_Annual_Report_2024_25-310202.pdf"

ingest_report "ICICIBANK" \
  "ICICIBANK-FY2025-annual-report.pdf" \
  "https://www.icici.bank.in/content/dam/icicibank/managed-assets/docs/investor/annual-reports/2025/icici-bank-integrated-report-2024-25.pdf"

ingest_report "SBIN" \
  "SBIN-FY2025-annual-report.pdf" \
  "https://sbi.co.in/documents/17826/35696/Annual%2BReport%2BFY2025.pdf/1b6a1b79-a16d-b9d1-d28f-be8d7edf60d5?t=1745556744202"

ingest_report "ITC" \
  "ITC-FY2025-annual-report.pdf" \
  "https://itcportal.com/content/dam/itc-corporate/open-pdfs/report-and-accounts/ITC-Report-and-Accounts-2025.pdf"

ingest_report "HINDUNILVR" \
  "HINDUNILVR-FY2025-annual-report.pdf" \
  "https://www.hul.co.in/files/annual-report-2024-25.pdf"

ingest_report "LT" \
  "LT-FY2025-annual-report.pdf" \
  "https://investors.larsentoubro.com/pdf/2025/Integrated%20Report%202024-25.pdf"

ingest_report "MARUTI" \
  "MARUTI-FY2025-annual-report.pdf" \
  "https://www.marutisuzuki.com/content/dam/arena-eds/corporate/pdf/company-reports/2024-2025/MSIL_IR_2024_25_HR.pdf"

ingest_report "SUNPHARMA" \
  "SUNPHARMA-FY2025-annual-report.pdf" \
  "https://sunpharma.com/wp-content/uploads/2025/07/Sunpharmaannualreport202425.pdf"

ingest_report "ASIANPAINT" \
  "ASIANPAINT-FY2025-annual-report.pdf" \
  "https://static.asianpaints.com/content/dam/annual-folder-2425/pdf/Asian%20Paints%20IR%202024-25.pdf"

ingest_report "WIPRO" \
  "WIPRO-FY2025-annual-report.pdf" \
  "https://www.wipro.com/content/dam/nexus/en/investor/annual-reports/2024-2025/Integrated-Annual-report-2024-2025.pdf"

ingest_report "AXISBANK" \
  "AXISBANK-FY2025-annual-report.pdf" \
  "https://www.axisbank.com/docs/default-source/annual-reports/for-axis-bank/annual-report-for-the-year-2024-2025.pdf"

ingest_report "BHARTIARTL" \
  "BHARTIARTL-FY2025-annual-report.pdf" \
  "https://www.airtel.in/airtel-annual-report-2024-25/pdf/Bharti%20Airtel%20IAR%202024-25.pdf"

echo "All annual reports processed successfully."
