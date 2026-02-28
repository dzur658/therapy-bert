# for development purposes, in order to allow for interactive exploration of the database
docker run -p 8000:8000 \
  -v $(pwd)/patients:/database \
  -e LBUG_FILE=patient_001_graph.lbug \
  --rm ghcr.io/ladybugdb/explorer:latest