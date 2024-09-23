docker exec -it kafka-0 bash

# Inside the kafka-0 container, run:
/opt/bitnami/kafka/bin/kafka-topics.sh --create \
  --bootstrap-server kafka-0:9092 \
  --topic mytopic \
  --partitions 3 \
  --replication-factor 3

# Verify the topic configuration
/opt/bitnami/kafka/bin/kafka-topics.sh --describe \
  --bootstrap-server kafka-0:9092 \
  --topic mytopic
