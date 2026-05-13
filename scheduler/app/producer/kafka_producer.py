from kafka import KafkaProducer
import json


class KafkaProducerHandler:
    _instance = None

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    
   
    def send_message(self, topic: str, messages: dict):
        for message in messages:
            
            self.producer.send(topic, value=message)
        
        self.producer.flush()

