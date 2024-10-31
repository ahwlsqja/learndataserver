import os
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile

from app.service.gpt_service import generate_conversation_pairs, get_gpt_response
from app.service.s3_service import download_from_s3, get_latest_audio_file, get_latest_version, upload_file_to_s3
from app.service.whisper import transcribe_audio

router = APIRouter()

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

@router.get("/transcribe/{model_id}")
async def transcribe(model_id: str):
    print('[INFO] ROUTER transcribe')
    latest_file_name = await get_latest_audio_file(model_id)
    
    if latest_file_name is None:
        raise HTTPException(status_code=404, detail="해당 모델 ID에 대한 오디오 파일이 없습니다.")

    downloaded_file_path = await download_from_s3(latest_file_name)
    
    if "Error" in downloaded_file_path:
        raise HTTPException(status_code=404, detail=downloaded_file_path)

    transcription = await transcribe_audio(downloaded_file_path)

    os.remove(downloaded_file_path)

    conversation = await get_gpt_response(transcription)

    print(f'[INFO] ROUTER transcribe - conversation: {conversation}')

    latest_version = await get_latest_version(model_id)
    
    content_path = await generate_conversation_pairs(model_id, latest_version, conversation)
    
    with open(content_path, 'rb') as f:
        file_content = BytesIO(f.read())
        upload_file = UploadFile(filename=content_path, file=file_content)
    
    result = await upload_file_to_s3(model_id, latest_version, upload_file)

    return result
