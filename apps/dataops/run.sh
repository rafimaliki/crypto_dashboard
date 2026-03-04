docker compose -p dataops down

docker compose -p dataops up postgres kafka -d

sleep 3s
docker exec dataops-kafka-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --create --topic btc_usd

sleep 3s
docker compose -p dataops up listener persistence -d
