from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry.protobuf import ProtobufDeserializer
from confluent_kafka.serialization import (
    StringDeserializer,
    SerializationContext,
    MessageField,
)
from proto import news_message_pb2  # generated from .proto

# from confluent_kafka.schema_registry import SchemaRegistryClient


def main():
    # schema_registry_conf = {
    #     "url": "http://localhost:8081"
    # }  # Change to your schema registry URL
    # schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    protobuf_deserializer = ProtobufDeserializer(
        news_message_pb2.NewsMessage,
        # schema_registry_client,
        conf={"use.deprecated.format": True},
    )
    string_deserializer = StringDeserializer("utf_8")

    consumer_conf = {
        "bootstrap.servers": "localhost:9092",
        "group.id": "news_group",
        "auto.offset.reset": "earliest",
    }

    consumer = Consumer(consumer_conf)
    consumer.subscribe(["scraped-news"])

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(msg.error())
                break

        key = string_deserializer(
            msg.key(), SerializationContext(msg.topic(), MessageField.KEY)
        )
        news_message = protobuf_deserializer(
            msg.value(), SerializationContext(msg.topic(), MessageField.VALUE)
        )
        if news_message is not None:
            print(f"Consumed record with key {key}: {news_message}")

    consumer.close()


if __name__ == "__main__":
    main()
