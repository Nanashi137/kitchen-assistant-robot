BACKEND_ENV_FILE := backend/.env


up:
	docker-compose --env-file $(BACKEND_ENV_FILE) up --build

down:
	docker-compose stop