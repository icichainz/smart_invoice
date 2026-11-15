# Smart Invoice

An invoicing app: a Django REST API (`main/`, project settings in `smart_invoice/`) with a React frontend (`frontend/`).

## Local setup

```bash
# Backend
cp .env.example .env              # then edit values as needed
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver       # http://localhost:8000

# Frontend (in a second terminal)
cd frontend && npm install && npm start   # http://localhost:3000

# Tests
python3 manage.py test main
```

Configuration is read from environment variables (or `.env`); see `.env.example` for the full list. With `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` must be set.
