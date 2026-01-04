
up:
	docker-compose --env-file .env -p karb up --build

down:
	docker-compose --env-file .env -p karb down