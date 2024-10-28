import pika

# RabbitMQ 연결 설정
connection = pika.BlockingConnection(pika.ConnectionParameters(
    host='localhost',
    credentials=pika.PlainCredentials('mo', 'mo')
))
channel = connection.channel()

# 큐 생성
channel.queue_declare(queue='audio_data_queue', durable=False)

print("audio_data_queue created.")
connection.close()
