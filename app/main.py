import asyncio
import json
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiohttp import ClientSession
from contextlib import asynccontextmanager
import pika  # RabbitMQ 클라이언트 라이브러리
from app.router.containers import RabbitMQContainer
from app.router.router import router, transcribe  # get_conversation을 가져옵니다.

# 전역 이벤트 루프 변수
global_event_loop = None

def get_or_create_event_loop():
    global global_event_loop
    if global_event_loop is None:
        global_event_loop = asyncio.get_event_loop()  # 현재 이벤트 루프 가져오기
        print(f"Created a new event loop with ID: {id(global_event_loop)}")
    else:
        print(f"Using existing event loop with ID: {id(global_event_loop)}")
    return global_event_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    global global_event_loop
    app.state.session = ClientSession()
    app.state.response_queues = {}
    app.state.convos = {}

    try:
        connection = RabbitMQContainer.connection()  # RabbitMQ 연결 가져오기
        app.state.rabbit_channel = connection.channel()  # 채널 생성

        # 큐가 존재하는지 확인하고 없으면 생성
        try:
            app.state.rabbit_channel.queue_declare(queue='audio_data_queue', passive=True)  # 큐가 존재하는지 확인
            print("audio_data_queue already exists.")
        except pika.exceptions.ChannelClosed:
            app.state.rabbit_channel.queue_declare(queue='audio_data_queue', durable=False)  # 큐 생성
            print("audio_data_queue created.")

        try:
            app.state.rabbit_channel.queue_declare(queue='datatolearnqueue', passive=True)
            print("datatolearnqueue already exists.")
        except pika.exceptions.ChannelClosed:
        # 채널이 닫힌 경우 다시 연결 시도
            app.state.rabbit_channel = connection.channel()
            app.state.rabbit_channel.queue_declare(queue='datatolearnqueue', durable=False)
            print("datatolearnqueue created.")
        except pika.exceptions.QueueNotFound:
    # 큐가 존재하지 않을 경우 생성
            app.state.rabbit_channel.queue_declare(queue='datatolearnqueue', durable=False)
            print("datatolearnqueue created.")


        # 응답 큐 생성

        # 이벤트 루프 생성
        get_or_create_event_loop()

        # 소비자 스레드 시작
        consumer_thread = threading.Thread(target=start_rabbitmq_consumer, args=(connection,))
        consumer_thread.start()

        yield  # 애플리케이션이 실행되는 동안 지속

    finally:
        await app.state.session.close()
        connection.close()  # 연결 종료

app = FastAPI(
    title='DATA API',
    summary='API Endpoints for ML Calls',
    docs_url='/',
    lifespan=lifespan,
)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the GPT-4 Mini API"}

def send_message(model_id: str, message: str):
    response_message = {"model_id": model_id, "message": message}
    
    try:
        if app.state.rabbit_channel.is_open:
            app.state.rabbit_channel.basic_publish(
                exchange='',
                routing_key='datatolearnqueue',
                body=json.dumps(response_message),
            )
            return {"status": "데이터 생성이 완료되었습니다.", "model_id": model_id, "message": message}
        else:
            print("Error: RabbitMQ channel is closed.")
            return {"status": "Error", "message": "RabbitMQ channel is closed."}
    except Exception as e:
        print(f"Error sending message: {e}")
        return {"status": "Error", "message": str(e)}

def callback_datatolearn(ch, method, properties, body):
    print("Received message from datatolearnqueue:", body)
    
def callback(ch, method, properties, body):
    print("Received message:", body)  # 수신한 메시지 로그
    data = json.loads(body.decode('utf-8'))
    model_id = data.get('data', {}).get('id')
    print(f"Model ID: {model_id}")

    # 응답을 result_queue로 전송
    response_message = {"status": "processing", "model_id": model_id}
    app.state.rabbit_channel.basic_publish(
        exchange='',
        routing_key='audio_data_queue',  # 응답 큐로 전송
        body=json.dumps(response_message),
    )
    print(f"Response sent to result_queue: {response_message}")


    if model_id:
        print(f"Preparing to transcribe model ID: {model_id}")  # 추가 로그
        loop = get_or_create_event_loop()
        
        try:
            print(f"Calling transcribe for model ID: {model_id}")  # 호출 로그 추가
            transcribe_future = asyncio.run_coroutine_threadsafe(transcribe(model_id), loop)
            transcribe_future.add_done_callback(lambda f: send_message(model_id, f.result()))

        except Exception as e:
            print(f"Error while running transcribe: {e}")

def start_rabbitmq_consumer(connection):
    print("Starting RabbitMQ consumer...")
    try:
        channel = connection.channel()
        print("RabbitMQ connection established.")

        channel.basic_consume(queue='audio_data_queue', on_message_callback=callback, auto_ack=True)
        print('Waiting for audio data messages. To exit press CTRL+C')
        channel.basic_consume(queue='datatolearnqueue', on_message_callback=callback_datatolearn, auto_ack=True)
        channel.start_consuming()
    except Exception as e:
        print(f"Error establishing RabbitMQ connection: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
