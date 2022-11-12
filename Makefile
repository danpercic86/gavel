RUN := poetry run
FLASK_ENV := FLASK_APP=runserver:app FLASK_ENV=development FLASK_RUN_HOST=0.0.0.0 FLASK_RUN_PORT=5005

setup: initialize.py config.yaml
	curl -sSL https://install.python-poetry.org | python3 -
	poetry config virtualenvs.in-project true
	poetry install
	$(RUN) python initialize.py


run: runserver.py config.yaml
	$(FLASK_ENV) $(RUN) flask run --extra-files config.yaml --reload

lint:
	$(RUN) black .
	$(RUN) djlint gavel/templates --reformat
	$(RUN) djlint gavel/templates --lint

build: Dockerfile docker-compose.yml
	docker compose up -d
