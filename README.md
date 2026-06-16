# Supplier Product Dashboard

POD product aggregation dashboard — search, compare, and discover products across multiple suppliers.

## Quick Start

### 1. Supabase Setup
1. Create a free project at https://supabase.com
2. Go to SQL Editor → run `supabase/schema.sql`
3. Copy `Project URL` and `service_role` key from Settings → API

### 2. GitHub Secrets
Add to GitHub repo Settings → Secrets → Actions:
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_KEY` — your service_role key

### 3. Local Development
```bash
# Scrapers
cd scrapers
pip install -r requirements.txt
cp .env.example .env  # Add SUPABASE_URL and SUPABASE_SERVICE_KEY
python boyada.py       # Test one scraper

# Frontend
cd frontend
npm install
cp .env.example .env.local  # Add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
npm run dev                  # http://localhost:3000
```

### 4. Deploy to Vercel
1. Import GitHub repo to Vercel
2. Set root directory to `frontend`
3. Add env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy

## Backup
- Supabase auto-backup daily (7-day retention, free tier)
- Manual export: use the Export button on the dashboard
- Code: git push to GitHub

## Adding a New Supplier
1. Create `scrapers/newsupplier.py` (copy an existing one as template)
2. Update parse_product_card with actual CSS selectors
3. Add to `.github/workflows/scrape.yml` as a new job
4. INSERT the supplier into the `suppliers` table

## Architecture

- **Scrapers:** Python + GitHub Actions (daily, 5 parallel jobs)
- **Database:** Supabase PostgreSQL (free tier, 500MB)
- **API:** Vercel Serverless Functions (search, export, stats)
- **Frontend:** Next.js + Tailwind CSS, Vercel hosting

## Tech Stack Cost

| Component | Choice | Cost |
|-----------|--------|------|
| Database | Supabase PostgreSQL | Free |
| Frontend hosting | Vercel | Free |
| API | Vercel Serverless Functions | Free |
| Scheduled jobs | GitHub Actions | Free |
| Code hosting | GitHub | Free |
| **Total** | | **$0/month** |
