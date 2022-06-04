RUN := poetry run

setup: initialize.py
	curl -sSL https://install.python-poetry.org | python3 -
	poetry config virtualenvs.in-project true
	poetry install
	$(RUN) python initialize.py


run: runserver.py
	$(RUN) python runserver.py

lint:
	$(RUN) black .

build: Dockerfile docker-compose.yml
	docker compose up -d
