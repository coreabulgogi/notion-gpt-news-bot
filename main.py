import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notion_client import Client as NotionClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # GitHub Actions에서는 필요 없지만 로컬 테스트 시 사용

# GPT 요약 함수
def summarize_news(news_text):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "당신은 유능한 뉴스 요약 전문가입니다. 주어진 기사를 간결하고 명확하게 요약해주세요."},
            {"role": "user", "content": news_text}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()


# 뉴스 크롤링 함수 (IT 동아 예시)
def fetch_news():
    url = "https://it.donga.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # 기사 제목 + 본문 링크 수집
    articles = soup.select("div.articleList div.articleList-title a")
    if not articles:
        raise Exception("기사를 찾을 수 없습니다.")

    first_article = articles[0]
    title = first_article.text.strip()
    link = first_article['href']

    # 기사 본문 가져오기
    article_response = requests.get(link)
    article_soup = BeautifulSoup(article_response.text, "html.parser")
    content = article_soup.select_one("div.article_txt").get_text(strip=True)

    return title, link, content


# Notion에 요약 내용 업로드
def upload_to_notion(title, summary, url):
    notion = NotionClient(auth=os.getenv("NOTION_TOKEN"))
    database_id = os.getenv("NOTION_DB_ID")

    today = datetime.today().strftime("%Y-%m-%d")

    notion.pages.create(
        parent={"database_id": database_id},
        properties={
            "날짜": {"date": {"start": today}},
            "제목": {"title": [{"text": {"content": title}}]},
            "요약": {"rich_text": [{"text": {"content": summary}}]},
            "URL": {"url": url}
        }
    )


# 메인 실행
def main():
    print("뉴스 가져오는 중...")
    title, link, content = fetch_news()

    print("GPT로 요약 중...")
    summary = summarize_news(content)

    print("Notion에 업로드 중...")
    upload_to_notion(title, summary, link)

    print("완료!")

if __name__ == "__main__":
    main()
