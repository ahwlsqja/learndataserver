from io import BytesIO
import json
import os
from aiohttp import ClientError
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile

# 환경 변수 로드
load_dotenv()

# S3 클라이언트 초기화
s3_bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
s3_bucket_name2 = os.getenv('AWS_S3_BUCKET_NAME2')

s3_region = os.getenv('AWS_REGION')
s3_client = boto3.client('s3', region_name=s3_region)

async def upload_to_s3(model_id: str, version: str, content: str) -> str:
    # 파일명 생성
    file_name = f"{model_id}_version_{version}.txt"
    json_content = json.dumps(content) 
    
    try:
        # S3에 파일 업로드
        s3_client.put_object(Bucket=s3_bucket_name, Key=file_name, Body=json_content)
        return f"파일이 업로드 되었습니다!: {file_name}"
    except NoCredentialsError:
        return "권한이 없습니다!"
    except Exception as e:
        return f"파일 업로드 중 오류: {str(e)}"
    
async def upload_audio_to_s3(model_id: str, file: UploadFile, version: int) -> str:
    try:
        object_name = f"{model_id}_version_{version}.mp3"
        s3_client.upload_fileobj(file.file, s3_bucket_name2, object_name)
        return f"https://{s3_bucket_name2}.s3.{s3_region}.amazonaws.com/{object_name}"
    
    except FileNotFoundError:
        return "파일이 없습니다!"
    except NoCredentialsError:
        return "권한이 없습니다!"
    except ClientError as e:
        return f"Error: {e}"

async def download_from_s3(object_name: str) -> str:
    try:
        print(object_name)
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "AudioFiles")
        if not os.path.exists(desktop_path):
            os.makedirs(desktop_path)  # 폴더가 없으면 생성

        download_path = os.path.join(desktop_path, object_name)   # 다운로드 경로
        s3_client.download_file(s3_bucket_name2, object_name, download_path)
        return download_path
    except ClientError as e:
        return f"Error: {e}"

async def get_latest_version(model_id: str) -> int:
    # 최상위 버전 구하는 로직 (S3에서 파일 목록을 가져와서 확인)
    existing_files = s3_client.list_objects_v2(Bucket=s3_bucket_name2, Prefix=f"{model_id}_version_")
    versions = [
        int(file['Key'].split('_version_')[1].split('.')[0]) 
        for file in existing_files.get('Contents', []) 
        if f"{model_id}_version_" in file['Key']
        ]
    
    return max(versions, default=0)  # 없으면 0 반환

async def get_latest_audio_file(model_id: str) -> str:
    print(123123)
    try:
        print(model_id)
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name2, Prefix=str(model_id))
        if 'Contents' not in response:
            return None
        print(response)
        # 파일 이름과 버전 추출
        files = [obj['Key'] for obj in response['Contents']]
        latest_file = max(files, key=lambda x: int(x.split('_')[-1].split('.')[0]))  # 예: model_id_version.mp3
        return latest_file
    except Exception as e:
        return f"Error: {e}"