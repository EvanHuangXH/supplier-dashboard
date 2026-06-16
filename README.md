# Supplier Product Dashboard

POD product aggregation dashboard — search, compare, and discover products across multiple suppliers.

## Setup

### Database
1. Create a Supabase project at https://supabase.com
2. Run `supabase/schema.sql` in the SQL Editor
3. Note your `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

### Scrapers
```bash
cd scrapers
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local with your Supabase credentials
npm run dev
```

## Architecture

- **Scrapers:** Python + GitHub Actions (daily)
- **Database:** Supabase PostgreSQL
- **API:** Vercel Serverless Functions
- **Frontend:** Next.js + Tailwind CSS (Vercel hosting)
