import json
import os
import redis
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.service.gpt_service import generate_conversation_pairs, get_gpt_response, make_gpt_response
from app.service.s3_service import download_from_s3, get_latest_audio_file, get_latest_version, upload_to_s3, upload_audio_to_s3
from app.service.whisper import classify_conversion, transcribe_audio
from typing import Dict
router = APIRouter()

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

cache: Dict[str, str] = {}

@router.post("/ask")
async def ask_gpt(model_id: str, version: str, prompt: str):
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    response = await get_gpt_response(prompt)
    print(response)

    # S3에 업로드
    upload_response = await upload_to_s3(model_id, version, response)

    return {"prompt": prompt, "response": response, "upload_status": upload_response}

@router.post("/audioupload")
async def upload_audio(model_id: str, file: UploadFile = File(...)):
    if file.content_type not in ["audio/mp3", "audio/wav"]:
        raise HTTPException(status_code=400, detail="MP3 형식만 업로드 해주세요!")
    
    if file.file.seek(0, 2) > MAX_FILE_SIZE:  # 파일 크기 확인
        raise HTTPException(status_code=400, detail="파일은 25MB이하만 업로드 가능합니다.")  
    file.file.seek(0)  # 파일 포인터를 처음으로 되돌리기
    version = await get_latest_version(model_id) + 1

    upload_response = await upload_audio_to_s3(model_id, file, version)
    
    return {"url": upload_response}


# @router.get("/transcribe/{model_id}")
async def transcribe(model_id: str):
    print(123123)
    latest_file_name = await get_latest_audio_file(model_id)
    
    if latest_file_name is None:
        raise HTTPException(status_code=404, detail="해당 모델 ID에 대한 오디오 파일이 없습니다.")

    # S3에서 파일 다운로드
    downloaded_file_path = await download_from_s3(latest_file_name)
    
    if "Error" in downloaded_file_path:
        raise HTTPException(status_code=404, detail=downloaded_file_path)

    # Whisper API에 전송하여 전사
    transcription = await transcribe_audio(downloaded_file_path)
    print(transcription)

    # Whisper API 호출이 성공적으로 완료되면 파일 삭제
    os.remove(downloaded_file_path)

    conversation = await get_gpt_response(transcription)

    redis_client.set(model_id, conversation)
    print(conversation)

    cache[model_id] = conversation
    print(conversation)
    return {"conversation": conversation}

@router.get("/conversation/{model_id}")
async def get_conversation(model_id: str):
    conversation = redis_client.get(model_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="캐시에 저장된 대화가 없습니다.")
    latest_version = await get_latest_version(model_id)
    conversation = conversation.decode('utf-8')
    conversations = await generate_conversation_pairs(conversation)
    await upload_to_s3(model_id, latest_version, conversations)

    json_file_path = "conversations.json"
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump({"conversations": conversations}, json_file, ensure_ascii=False, indent=4)

    # JSON 파일 다운로드
    return FileResponse(json_file_path, media_type='application/json', filename=json_file_path)

# @router.post("/whisper")
# async def audiototext(model_id: str, version: str):
#     file_name = f"{model_id}_version_{version}.mp3"
#     transcribe_audio_text = await transcribe_audio(file_name)

#     return {"file_name": file_name, "response": transcribe_audio_text}


