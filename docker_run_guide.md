- Use the project wrapper I added if you want docker-compose to always load the repo `.env`: ./docker/up.sh ...
- Replace service names (api, worker) or image/container names as needed.

1) Build images

- With docker-compose (build all services defined in docker-compose.yml):
```bash
# from repo root
./docker/up.sh build --no-cache
# or to build a single service (faster)
./docker/up.sh build api
```

- Plain docker (build the app image using the Dockerfile):
```bash
# builds an image named 'webrag_api' from the Dockerfile, context is repo root
docker build -t webrag_api -f docker/Dockerfile ..
```

2) Run (start) containers that are already built

- If you used docker-compose previously and containers already exist (created), start them without rebuilding or recreating:
```bash
# start previously-created containers (no build, no recreate)
docker-compose -f docker/docker-compose.yml start

# or with wrapper (also ensures .env is loaded)
./docker/up.sh start
```

- If containers don't exist yet but you want to create and run them using the existing images (no build):
```bash
# create/start containers from existing images, do not build
docker-compose --env-file .env -f docker/docker-compose.yml up -d --no-build

# or start a single service
docker-compose --env-file .env -f docker/docker-compose.yml up -d --no-build api
```

- Plain docker (create & run a container from an already-built image):
```bash
# run a container named 'webrag_api' from image 'webrag_api', detached
docker run -d --name webrag_api --env-file .env -p 8000:8000 webrag_api

# if you want the container to restart automatically on host reboot:
docker run -d --name webrag_api --restart unless-stopped --env-file .env -p 8000:8000 webrag_api
```

To start a specific stopped container (created earlier with docker run):
```bash
docker start webrag_api
```

3) Stop containers without deleting them

- With docker-compose (stops services but leaves containers present):
```bash
docker-compose -f docker/docker-compose.yml stop

# or stop a single service
docker-compose -f docker/docker-compose.yml stop api
```

- With the wrapper:
```bash
./docker/up.sh stop
```

- Plain docker (stop a named container):
```bash
docker stop webrag_api
```

Useful follow-ups / quick checks
- Show all containers and status:
```bash
docker ps -a
# or
docker-compose -f docker/docker-compose.yml ps
```

- View logs (tail/follow):
```bash
./docker/up.sh logs --tail=200 api
# or
docker logs -f webrag_api
```

- Start stopped containers again:
```bash
docker start webrag_api                   # plain docker
docker-compose -f docker/docker-compose.yml start   # compose
./docker/up.sh start
```