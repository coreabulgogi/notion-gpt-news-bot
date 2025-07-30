import os
import requests
import openai
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Secret 환경변수 가져오기
openai.api_key = os.getenv("OPENAI_API_KEY")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

# ✅ 1. 뉴스 가져오기 (예: 연합뉴스 RSS)
def get_news():
    rss_url = "https://www.yonhapnewstv.co.kr/browse/feed/"
    response = requests.get(rss_url)
    if response.status_code != 200:
        raise Exception("뉴스를 불러오지 못했습니다.")

    from xml.etree import ElementTree as ET
    root = ET.fromstring(response.content)
    items = root.findall(".//item")
    news_list = []
    for item in items[:3]:  # 상위 3개만
        title = item.find("title").text
        description = item.find("description").text
        link = item.find("link").text
        news_list.append(f"제목: {title}\n요약: {description}\n링크: {link}\n")
    return "\n\n".join(news_list)

# ✅ 2. GPT 요약
def summarize_news(news_content):
    prompt = f"""
다음은 오늘의 뉴스 목록입니다. 각 뉴스 항목을 2줄 이내로 간결하게 요약하고, 핵심 내용을 정리해주세요:

{news_content}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"].strip()

# ✅ 3. Notion에 저장
def save_to_notion(summary):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": f"📰 뉴스 요약 - {datetime.now().strftime('%Y-%m-%d')}"}}]
            },
            "내용": {
                "rich_text": [{"text": {"content": summary}}]
            }
        }
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        raise Exception(f"Notion 저장 실패: {res.text}")

# ✅ 실행
if __name__ == "__main__":
    print("뉴스 가져오는 중...")
    news = get_news()

    print("GPT로 요약 중...")
    summary = summarize_news(news)

    print("Notion에 저장 중...")
    save_to_notion(summary)

    print("완료!")
