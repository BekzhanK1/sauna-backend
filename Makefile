.PHONY: runserver celery beat migrate makemigrations shell

# Run Django development server
run:
	python3 manage.py runserver

# Run Celery worker
celery:
	celery -A sauna worker -l info

# Run Celery beat scheduler
beat:
	celery -A sauna beat -l info

# Run both Celery worker and beat (separate terminals recommended)
celery_all:
	celery -A sauna worker -l info & celery -A sauna beat -l info

# Make migrations
makemigrations:
	python3 manage.py makemigrations

# Apply migrations
migrate:
	python3 manage.py migrate

# Open Django shell
shell:
	python3 manage.py shell
