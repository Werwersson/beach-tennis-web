web: python -m flask --app wsgi db upgrade && python -m flask --app wsgi seed && gunicorn wsgi:app --workers 2 --bind 0.0.0.0:$PORT
