# Nyay Vision — Metrology Guard AI

An AI-assisted packaging label audit workspace for common retail declarations under India’s Legal Metrology (Packaged Commodities) Rules, 2011. The application is split into `backend/` (FastAPI, OpenAI vision, SQLite, PDF reports) and `frontend/` (React + Vite dashboard).

## Start locally

Requirements: Python 3.10+ and Node.js 18+.

1. Configure the backend:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   ```

2. Add your OpenAI API key to `backend/.env` (`OPENAI_API_KEY=...`). The vision flow uses the OpenAI Responses API. The key stays server-side. The default is `gpt-4.1-mini` with `gpt-4.1` fallback; set model IDs available to your OpenAI project as needed.

3. Start the API from `backend/`:

   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. In a second terminal:

   ```bash
   cd frontend
   npm install
   cp .env.example .env
   npm run dev
   ```

Open the Vite URL (normally `http://localhost:5173`). API docs are at `http://localhost:8000/docs`. SQLite data and generated PDFs are stored in `backend/data/`.

## Vercel frontend connection

Deploy the FastAPI backend separately from the Vercel frontend. In Vercel project settings, set `VITE_API_URL` to the backend's public base URL (for example, `https://your-api.example.com`, with no trailing slash) and redeploy the frontend. The local `frontend/.env` value points to `localhost` and is only for local development. The backend accepts Vercel preview/production origins; for a custom frontend domain, set `CORS_ALLOW_ORIGINS` on the backend to that full origin.

## What works

- Single image or combined multi-view (up to 10 images of the same product) audits with OpenAI vision extraction and model fallback.
- Strict structured output for extracted label text and per-field `box_2d` coordinates on a 0–1000 grid.
- Automatic category inference from the package image; no manual product/business/offence selections.
- Category-aware rules: FSSAI checks are limited to food; general non-food products are not failed for an absent expiry date; medicines and selected regulated groups use product-specific checks or request review.
- Date normalization, confidence-aware screening score, and conditional penalty exposure based on the applicable statute.
- Persistent scan history, scan details, and downloadable inspection summary PDFs.
- Browser IndexedDB queue for uploads made while offline; queued files automatically submit when connected.
- API health status and key configuration status in the dashboard.

## Legal and operational limits

This is an AI-assisted first-pass screening aid. Package classification, exemptions, amendments, declarations, legibility, quantity tolerances, and enforcement depend on facts and current rules. The product image cannot reveal prior offence history, so Legal Metrology section 36 exposure is shown by offence stage: first offence improvement notice, second offence penalty up to INR 5 lakh, and subsequent offences INR 25–50 lakh. These are statutory stages, not a prediction of the penalty an authority will impose. Food-label risk may separately reference the Food Safety and Standards Act section 52 cap; overlapping amounts are not added. The app does not issue a government challan or legal notice.

Rule references checked against the Department of Consumer Affairs' [Legal Metrology rules and amendments](https://consumeraffairs.gov.in/pages/legal-metrology-act), the [Jan Vishwas (Amendment of Provisions) Act, 2026](https://consumeraffairs.gov.in/public/upload/files/2026.4.8%20Jan%20Vishwas%20Act%202026_1777014384.pdf), FSSAI's [Labelling and Display Regulations](https://www.fssai.gov.in/upload/uploadfiles/files/Comp_Labelling%20Display_Version%20VIII_09_09_2025.pdf), and the CDSCO [Cosmetics Rules, 2020](https://cdsco.gov.in/opencms/resources/UploadCDSCOWeb/2022/cos_rules/Cosmetics%20Rules%202020.pdf). Product-specific provisions and later amendments still require review where the app flags them.
