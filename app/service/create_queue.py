import pika

import os
from dotenv import load_dotenv
load_dotenv()

RABBITMQ_CREDENTIAL1 = os.getenv('RABBITMQ_CREDENTIAL1')
RABBITMQ_CREDENTIAL2 = os.getenv('RABBITMQ_CREDENTIAL2')
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
RABBITMQ_PORT = os.getenv('RABBITMQ_PORT')

# RabbitMQ 연결 설정
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host=RABBITMQ_HOST,
    credentials=pika.PlainCredentials(RABBITMQ_CREDENTIAL1, RABBITMQ_CREDENTIAL2)
))
channel = connection.channel()

# 큐 생성
channel.queue_declare(queue='audio_data_queue', durable=False)

print("audio_data_queue created.")
connection.close()
