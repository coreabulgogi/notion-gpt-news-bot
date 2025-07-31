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
    url = "https://www.fashionbiz.co.kr/" # URL 변경!
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # --- 기사 목록 셀렉터 수정 ---
    # 캡쳐 화면을 바탕으로 추정:
    # 1. '최신 기사' <h3> 태그를 찾고,
    # 2. 그 다음 나오는 형제 요소인 기사 리스트를 감싸는 div (class="sc-221d63dd-2 cARbOc")를 찾은 후,
    # 3. 그 안에서 각 기사 링크 (a 태그)를 찾습니다.
    
    # 1단계: '최신 기사' <h3> 태그 찾기
    latest_news_heading = soup.find("h3", string="최신 기사") 
    
    articles = []
    if latest_news_heading:
        # 2단계: '최신 기사' heading 바로 다음 형제 요소인 div (기사 리스트 컨테이너) 찾기
        # 이 div의 클래스명이 유동적이므로, sibling을 사용하는 것이 더 견고할 수 있습니다.
        # find_next_sibling으로 div 태그를 찾고, 그 안에서 모든 a 태그를 찾습니다.
        news_list_container = latest_news_heading.find_next_sibling("div")
        
        # 동적 클래스인 "sc-221d63dd-2 cARbOc"를 직접 지정하기는 어려우므로,
        # find_next_sibling("div")를 사용하거나, 아니면 news_list_container의 특정 속성을 활용해야 합니다.
        # 캡쳐 화면에서는 'sc-221d63dd-2 cARbOc' 이 class를 가진 div가 보입니다.
        # 하지만 이 클래스도 변동될 가능성이 있으니, 좀 더 일반적인 방법을 시도해봅니다.

        # 가장 간단하게는, 해당 컨테이너 내부의 모든 'a' 태그를 가져오는 방식입니다.
        if news_list_container:
            articles = news_list_container.find_all("a") # 컨테이너 안의 모든 <a> 태그를 기사 링크로 간주

    if not articles:
        raise Exception("패션비즈 웹사이트에서 기사를 찾을 수 없습니다. '최신 기사' 섹션 또는 기사 셀렉터 확인 필요.")

    first_article = articles[0]
    
    # --- 제목 셀렉터 수정 (캡쳐 화면에는 없지만, 일반적인 웹 구조 추정) ---
    # 기사 제목은 <a> 태그 안에 <p> 태그 (클래스 tit) 또는 <h3> 태그 등으로 있을 수 있습니다.
    # 이전 캡쳐에서 p.tit 가 있었으므로, 우선 p.tit로 시도합니다.
    title_element = first_article.select_one("p.tit")
    if not title_element:
        # 만약 p.tit가 없으면, <a> 태그 자체의 텍스트를 제목으로 시도합니다.
        # 또는 <a> 태그 내의 <h3>, <span> 등을 찾아봐야 합니다.
        title = first_article.get_text(strip=True) 
    else:
        title = title_element.get_text(strip=True)

    link = first_article['href']
    # 링크가 상대 경로일 경우 (예: /news/articleView.html?idxno=12345) 절대 경로로 변환
    if not link.startswith('http'):
        link = "https://www.fashionbiz.co.kr" + link


    # --- 기사 본문 셀렉터 수정 ---
    # 이 부분은 현재 캡쳐로 알 수 없습니다. 실제 기사 페이지로 이동하여 본문 HTML을 확인해야 합니다.
    # 임시로 가장 흔한 셀렉터 중 하나를 넣겠습니다.
    # 여러분이 직접 기사 페이지에서 본문 내용을 감싸는 HTML 요소의 정확한 셀렉터를 찾아야 합니다.
    article_response = requests.get(link)
    article_soup = BeautifulSoup(article_response.text, "html.parser")

    # 예시: 기사 본문이 'div#article-content' 또는 'div.article_body_content' 안에 있다고 가정
    content_element = article_soup.select_one("div#article-content") # <<< 이 부분을 실제 기사 페이지에서 확인 후 수정!
    if not content_element:
        # 다른 흔한 셀렉터들을 시도해 볼 수도 있습니다.
        content_element = article_soup.select_one("div.article-view-content")
        if not content_element:
            content_element = article_soup.select_one("div.txt_view")
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
