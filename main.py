import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from notion_client import Client as NotionClient
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() # GitHub Actions에서는 secrets로 주입되므로 실제 동작에 영향 없음

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

# 뉴스 크롤링 함수 (패션비즈 웹사이트에 맞게 재수정)
def fetch_news():
    url = "https://www.fashionbiz.co.kr/" # URL 변경!
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # --- 기사 목록 셀렉터 수정 ---
    # 1단계: '최신 기사' <h3> 태그를 찾습니다.
    latest_news_heading = soup.find("h3", string="최신 기사") 
    
    articles = []
    if latest_news_heading:
        # 2단계: '최신 기사' heading 바로 다음 형제 요소인 div (기사 리스트 컨테이너)를 찾습니다.
        # 캡쳐 화면에서 클래스가 'sc-221d63dd-2 cARbOc' 였지만, 동적 클래스이므로 find_next_sibling("div")를 사용합니다.
        news_list_container = latest_news_heading.find_next_sibling("div")
        
        if news_list_container:
            # 3단계: 컨테이너 안에서 각 기사 링크 (<a> 태그)를 찾습니다.
            # 각 기사가 <div>로 감싸여 있고 그 안에 <a>가 있을 것으로 추정
            # .sc-53c9553f-0 ksjQKq 는 각 기사 아이템 div의 클래스
            articles = news_list_container.select("div.sc-53c9553f-0.ksjQKq > a") 
            # 만약 위 셀렉터가 안된다면, 단순히 news_list_container.find_all("a") 로 시도해 볼 수 있습니다.
            # articles = news_list_container.find_all("a") 
            
    if not articles:
        raise Exception("패션비즈 웹사이트에서 기사를 찾을 수 없습니다. '최신 기사' 섹션 또는 기사 셀렉터 확인 필요.")

    first_article = articles[0]
    
    # --- 제목 추출 ---
    # 이전 캡쳐 (image_5afa60.jpg)에서 'p.tit'으로 추정했었으므로, 일단 이걸 유지합니다.
    # 만약 안되면, first_article.get_text(strip=True)를 사용해보세요.
    title_element = first_article.select_one("p.tit")
    if title_element:
        title = title_element.get_text(strip=True)
    else:
        # p.tit이 없으면 <a> 태그의 전체 텍스트를 제목으로 시도 (혹은 <a> 내부의 다른 제목 태그를 찾아야 함)
        title = first_article.get_text(strip=True)

    link = first_article['href']
    # 링크가 상대 경로일 경우 (예: /news/articleView.html?idxno=12345) 절대 경로로 변환
    if not link.startswith('http'):
        link = "https://www.fashionbiz.co.kr" + link

    # --- 기사 본문 셀렉터 ---
    # 이 부분은 여전히 직접 확인해야 합니다. 아래는 가장 흔한 예시입니다.
    # 실제 기사 페이지로 이동하여 본문 내용을 감싸는 정확한 태그/클래스/ID를 찾아야 합니다.
    article_response = requests.get(link)
    article_soup = BeautifulSoup(article_response.text, "html.parser")

    # 예시: 기사 본문이 'div#article-content' 또는 'div.article_body_content' 안에 있다고 가정
    content_element = article_soup.select_one("div#article-content") 
    if not content_element:
        content_element = article_soup.select_one("div.article-view-content")
        if not content_element:
            content_element = article_soup.select_one("div.txt_view")
            if not content_element:
                raise Exception(f"기사 본문 내용을 찾을 수 없습니다: {link}. 실제 기사 페이지의 셀렉터를 확인하세요.")

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
