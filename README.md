# Smart Invoice

An invoicing app: a Django REST API (`main/`, project settings in `smart_invoice/`) with a React frontend (`frontend/`).

## Local setup

```bash
# Backend (requires Python 3.12+ for Django 6.1)
python3 -m venv .venv && source .venv/bin/activate
cp .env.example .env              # then edit values as needed
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver        # http://localhost:8000

# Frontend (in a second terminal)
cd frontend && npm install && npm start   # http://localhost:3000

# Tests
python manage.py test main
```

Configuration is read from environment variables (or `.env`); see `.env.example` for the full list. With `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` must be set.
