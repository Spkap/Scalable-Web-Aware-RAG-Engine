# 1) Root
curl -i http://localhost:8001/

# 2) Health
curl -sS http://localhost:8001/health | jq .

# 3) Ingest a URL (start an ingestion job)
curl -i -X POST "http://localhost:8001/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}'

# 3a) Ingest and capture job_id into a shell variable (requires jq)
JOB_JSON=$(curl -sS -X POST "http://localhost:8001/ingest-url" -H "Content-Type: application/json" -d '{"url":"https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}')
echo "$JOB_JSON" | jq .
JOB_ID=$(echo "$JOB_JSON" | jq -r '.job_id')
echo "JOB_ID=$JOB_ID"

# 4) Check a job status (replace <JOB_ID> or use $JOB_ID)
curl -i "http://localhost:8001/status/<JOB_ID>"
# or (if captured above)
curl -sS "http://localhost:8001/status/${JOB_ID}" | jq .

# 4a) Poll until completion (bash loop)
while true; do
  s=$(curl -sS "http://localhost:8001/status/${JOB_ID}" | jq -r '.status')
  echo "$(date +%T) status=$s"
  if [ "$s" = "completed" ] || [ "$s" = "failed" ]; then break; fi
  sleep 2
done

# 5) Query the knowledge base (plain)
curl -i -X POST "http://localhost:8001/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is retrieval augmented generation?","top_k":5}'

# 5a) Query and pretty-print
curl -sS -X POST "http://localhost:8001/query" -H "Content-Type: application/json" \
  -d '{"question":"What is retrieval augmented generation?","top_k":5}' | jq .

# 5b) Query with filters (example: filter by source_url)
curl -sS -X POST "http://localhost:8001/query" -H "Content-Type: application/json" \
  -d '{"question":"What is RAG?","top_k":3,"filters":{"source_url":"https://en.wikipedia.org/wiki/Retrieval-augmented_generation"}}' | jq .

# 6) Invalid ingestion examples (expect 400 or 422)
curl -i -X POST "http://localhost:8001/ingest-url" -H "Content-Type: application/json" -d '{"url":"not-a-url"}'
curl -i -X POST "http://localhost:8001/ingest-url" -H "Content-Type: application/json" -d '{"url":""}'

# 7) Empty query example (expect 422)
curl -i -X POST "http://localhost:8001/query" -H "Content-Type: application/json" -d '{"question":""}'

# 8) OpenAPI docs
open "http://localhost:8001/docs"   # macOS: opens default browser
# or just fetch HTML
curl -sS http://localhost:8001/docs | sed -n '1,40p'