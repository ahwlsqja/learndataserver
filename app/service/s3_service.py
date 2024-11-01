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

async def upload_file_to_s3(model_id: str, version: int, file: UploadFile) -> str:
    try:
        object_name = f"{model_id}_version_{version+1}.jsonl"
        s3_client.upload_fileobj(file.file, s3_bucket_name, object_name)
        return f"https://{s3_bucket_name}.s3.{s3_region}.amazonaws.com/{object_name}"
    
    except FileNotFoundError:
        return "파일이 없습니다!"
    except NoCredentialsError:
        return "권한이 없습니다!"
    except ClientError as e:
        return f"Error: {e}"

async def download_from_s3(object_name: str) -> str:
    print('[INFO] EXECUTE download_from_s3()')
    curr_path = os.path.dirname(os.path.realpath(__file__))
    audio_dir_path = os.path.join(curr_path, 'audios')

    try:
        print(f'[INFO] download_from_s3() - object_name: {object_name}')
        if not os.path.exists(audio_dir_path):
            os.makedirs(audio_dir_path)  # 폴더가 없으면 생성

        download_path = os.path.join(audio_dir_path, object_name)   # 다운로드 경로
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
    print('[INFO] EXECUTED get_latest_audio_file()')

    try:
        print(f'[INFO] get_latest_audio_file() - model_id: {model_id}')
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name2, Prefix=str(model_id))

        if 'Contents' not in response:
            return None
        # print(response)

        # 파일 이름과 버전 추출
        files = [obj['Key'] for obj in response['Contents']]
        latest_file = max(files, key=lambda x: int(x.split('_')[-1].split('.')[0]))  # 예: model_id_version.mp3
        return latest_file
    
    except Exception as e:
        return f"Error: {e}"