

- 1. Start all services using the wrapper script (run from the project root)
./docker/up.sh up --build -d

- 2. Check the running containers
docker ps

- 3. Check the system health
curl http://localhost:8000/health

- 4. Ingest the URL (replace with your chosen URL if different)
curl -X POST "http://localhost:8000/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}'

- 5. Check the job status (you will get the {job_id} from the previous command)
- Example: curl http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000
curl http://localhost:8000/status/{job_id}

- 6. Tail the logs of a worker to show processing (run this in a separate terminal)
docker logs -f webrag_worker_1

- 7. Query the knowledge base
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the core components of a RAG system?"}'

- 8. (Optional) Second query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "How does RAG reduce hallucinations in language models?"}'

- 9. Stop all services when you are finished
./docker/up.sh down