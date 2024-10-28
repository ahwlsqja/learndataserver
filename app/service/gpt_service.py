import asyncio
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')

openai = OpenAI(api_key=openai_api_key)

async def get_gpt_response(transcription: str) -> str:
    prompt = f"""
    아래는 두 사람 간의 대화입니다. 각 발언을 '나:'와 '상대:' 형식으로 나누어 주세요.

    대화 내용:
    {transcription}

    변환된 대화:
    """

    response = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    res = response.choices[0].message.content
    resp = res.split('\n')
    print(f'Response: {resp}')
    return resp




async def make_gpt_response(resp: list[str]) -> str:
    instruction = [conv for conv in resp if '나: ' in conv]
    output = [conv for conv in resp if '상대: ' in conv]
    if len(instruction) > len(output):
        instruction = instruction[:-1]
    elif len(output) > len(instruction):
        output = output[1:]
    prompt = f"""
    Below is a pair of conversation between two people.

    {{
        "instruction": {instruction},
        "output": {output}
    }}

    Consider the relationship between the two and create about 20 pairs of conversations that are very similar in context to this one.
    And match the response in the form of json file with parameters 'instruction' and 'output'.
    Make sure to follow the specified tone: if it's a dialect, use a dialect; if it's standard language, use standard language.
    The number of generated 'instruction' and 'output' items must be equal.

    '{{
        instruction: [ 한글로 생성, , , , ...],
        output: [한글로 생성 , , , , ...]
    }}'

    Only output the resulting JSON data, without any additional text.
"""
    
    response = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

async def generate_conversation_pairs(transcription: str, target_count: int = 2000) -> list:
    all_conversations = {
        'instruction': [],
        'output':  []
    }
    
    while len(all_conversations) < target_count:
        # API 호출로 대화쌍 생성
        new_conversations = await make_gpt_response(transcription)
        print(new_conversations)
        new_conversations = new_conversations.replace('json', '')
        new_conversations = new_conversations.replace("```", "")
        print(new_conversations)

        pairs = eval(new_conversations)
        all_conversations['instruction'].extend(pairs['instruction'])
        all_conversations['output'].extend(pairs['output'])
        # 생성된 대화쌍을 리스트에 추가
        # 중복된 대화쌍을 제거하고, 최대 수를 유지

        print(f"현재까지 생성된 대화쌍 수: {len(all_conversations['instruction'])}")

        # 요청 간 지연 추가 (예: 1초)
        await asyncio.sleep(2)  # API 호출을 위한 지연
    print("데이터 생성이 완료되었습니다!")
    return all_conversations  # 목표 수 만큼만 반환


