# Photo-Dump

Phase 1 implements account auth, albums, image upload, gallery browsing, download URLs, immediate metadata records, and asynchronous image processing hooks.

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Production backend commands

Render can run the Django API with:

```bash
cd backend && python manage.py migrate && python manage.py collectstatic --noinput
cd backend && gunicorn home.wsgi:application
```

Run the worker as a separate background worker service:

```bash
cd backend && celery -A home worker -l info
```

## Supabase setup

1. Create a fresh Supabase project.
2. In Project Settings > Database, copy the pooled Postgres connection string and set it as `DATABASE_URL` in `backend/.env`.
3. In Project Settings > API, copy the project URL into `SUPABASE_URL`.
4. Copy the `service_role` key into `SUPABASE_SERVICE_ROLE_KEY`. Keep this server-only.
5. In Storage, create a private bucket named `photos`.
6. Set `MEDIA_STORAGE_BACKEND=supabase`.
7. Run `python manage.py migrate` so Django creates the Phase 1 tables in Supabase Postgres.

The app stores storage keys, not permanent public URLs. API responses generate short-lived URLs through the media service abstraction.

## Worker setup

Run Redis locally or point `CELERY_BROKER_URL` at a managed Redis instance.

```bash
cd backend
celery -A home worker -l info
```

Uploads create `Photo` rows immediately. Thumbnail generation, preview generation, dimensions, and EXIF extraction are handled by the Celery task.

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://localhost:8000/api` if the API is not running on the default local URL.
