RUN := poetry run

setup: initialize.py config.yaml
	curl -sSL https://install.python-poetry.org | python3 -
	poetry config virtualenvs.in-project true
	poetry install
	$(RUN) python initialize.py


run: runserver.py config.yaml
	$(RUN) flask --app runserver:app run --extra-files config.yaml --reload --host 0.0.0.0 --port 5005 --debugger

lint:
	$(RUN) black .
	$(RUN) djlint gavel/templates --reformat
	$(RUN) djlint gavel/templates --lint

build: Dockerfile docker-compose.yml
	docker compose up -d
