import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notion_client import Client as NotionClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# GPT 요약 함수 (변경 없음)
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

# 뉴스 크롤링 함수 (패션비즈 웹사이트에 맞게 수정)
def fetch_news():
    url = "https://www.fashionbiz.co.kr/" # <<< URL 변경!
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # --- 기사 목록 셀렉터 수정 ---
    # 스크린샷에서 '최신 기사' 섹션 아래 ul.list_news > li > a 로 추정
    # 실제 개발자 도구로 '4050 플랫폼...' 기사 제목을 클릭하여 정확한 셀렉터를 확인하세요.
    articles = soup.select("ul.list_news > li > a") # <<< 이 부분을 확인 후 수정!

    if not articles:
        # 혹시 다른 섹션이 있다면 (예: 메인 섹션의 큰 기사), 다른 셀렉터를 추가로 시도해볼 수 있습니다.
        # 예: articles = soup.select("div.main-news-section a.news-link")
        # 여러 셀렉터를 시도하려면 아래 if not articles: 이전에 다른 셀렉터로 재시도 로직 추가.
        raise Exception("패션비즈 웹사이트에서 기사를 찾을 수 없습니다. 셀렉터 확인 필요.")

    first_article = articles[0]
    title = first_article.select_one("p.tit").get_text(strip=True) # <<< 제목 셀렉터 수정!
    link = first_article['href']

    # --- 기사 본문 셀렉터 수정 ---
    # 실제 기사 페이지로 이동하여 본문 내용을 감싸는 정확한 태그/클래스/ID를 찾아야 합니다.
    # 스크린샷으로는 알 수 없으므로, 직접 기사 하나를 클릭해서 확인해야 합니다.
    article_response = requests.get(link)
    article_soup = BeautifulSoup(article_response.text, "html.parser")

    # 이 셀렉터는 **가장 중요한 부분**이며, 실제 기사 페이지의 본문 HTML 구조에 따라 달라집니다.
    # 예시: 기사 본문이 'div#article_body' 또는 'div.view_txt' 안에 있다면
    content_element = article_soup.select_one("div.view_txt") # <<< 이 부분을 확인 후 수정!
    if not content_element:
        raise Exception(f"기사 본문 내용을 찾을 수 없습니다: {link}. 셀렉터 확인 필요.")

    content = content_element.get_text(strip=True)

    return title, link, content


# Notion에 요약 내용 업로드 (변경 없음)
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

# 메인 실행 (변경 없음)
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
