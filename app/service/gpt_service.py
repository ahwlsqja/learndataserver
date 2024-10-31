import os
import re
import json
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
    return resp

async def make_gpt_response(resp: list[str]) -> str:
    print('[INFO] EXECUTE make_gpt_response()')

    instruction = [conv for conv in resp if '나: ' in conv]
    instruction = [ins.replace('나: ', '') for ins in instruction]
    output = [conv for conv in resp if '상대: ' in conv]
    output = [out.replace('상대: ', '') for out in output]

    if len(instruction) > len(output):
        instruction = instruction[:-1]
    elif len(output) > len(instruction):
        output = output[1:]

    print(f'[INFO] EXECUTE make_gpt_response() - conversations:\ninstruction: {instruction}\noutput: {output}')
    print(f'[INFO] EXECUTE make_gpt_response() - conversations:\ninstruction.length: {len(instruction)}\noutput.length: {len(output)}')

    prompt = f"""
    Below is a pair of conversation between two people.

    Instruction: {str(instruction)}
    Output: {str(output)}

    **Task**
    Use the given pair as a reference and generate approximately 50 more similar pairs of conversations.
    Then, format the results into a JSONL format for ChatGPT fine-tuning as follows:

    {{"messages": [{{"role": "system", "content": "You are an assistant tasked with providing engaging and relevant responses based on the given conversation context. Respond thoughtfully and appropriately to user inputs."}}, {{"role": "user", "content": "first instruction"}}, {{"role": "assistant", "content": "first output"}}]}}}}
    {{"messages": [{{"role": "system", "content": "You are an assistant tasked with providing engaging and relevant responses based on the given conversation context. Respond thoughtfully and appropriately to user inputs."}}, {{"role": "user", "content": "second instruction"}}, {{"role": "assistant", "content": "second output"}}]}}}}
    {{"messages": [{{"role": "system", "content": "You are an assistant tasked with providing engaging and relevant responses based on the given conversation context. Respond thoughtfully and appropriately to user inputs."}}, {{"role": "user", "content": "third instruction"}}, {{"role": "assistant", "content": "third output"}}]}}}}
    ...
    {{"messages": [{{"role": "system", "content": "You are an assistant tasked with providing engaging and relevant responses based on the given conversation context. Respond thoughtfully and appropriately to user inputs."}}, {{"role": "user", "content": "final instruction"}}, {{"role": "assistant", "content": "final output"}}]}}}}

    Don't print '...' or \' in the result.
    """
    
    response = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


async def generate_conversation_pairs(model_id: str, version: str, conversation: str, target_count: int = 2) -> str:
    file_path = f'{model_id}_version_{int(version)+1}.jsonl'

    with open(file_path, 'w', encoding='utf-8') as file:
        cnt = 0

        while cnt <= target_count:
            
            new_conversations = await make_gpt_response(conversation)
            new_conversations = new_conversations.replace('jsonl', '')
            new_conversations = new_conversations.replace('json', '')
            new_conversations = new_conversations.replace("```", "")
            res = new_conversations.split("\n")
            print(f'new_conversations: {res}')

            for line in res:
                print(f'line: {line}')

                try:
                    if line != '':
                        line = line.replace('\'', '\"')
                        json_line = json.loads(line)

                        if re.search('[a-zA-Z]', json_line['messages'][1]['content']) or \
                           re.search('[a-zA-Z]', json_line['messages'][2]['content']):
                            continue

                        json.dump(json_line, file, ensure_ascii=False)
                        file.write('\n')
                        
                except: pass

            cnt += 1

    return file_path
