FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Report PDF generation (services/report.py) uses Playwright's print-to-PDF —
# --with-deps installs the matching Chromium build plus whatever system
# libraries that build needs on this image.
RUN playwright install --with-deps chromium

COPY . .

RUN mkdir -p /app/uploads

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
