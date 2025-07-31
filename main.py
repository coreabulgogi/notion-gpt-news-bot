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

# 뉴스 크롤링 함수 (패션비즈 웹사이트에 맞게 재수정 - 동적 클래스 대응)
def fetch_news():
    url = "https://www.fashionbiz.co.kr/" # URL 변경!
    print(f"DEBUG: Accessing URL: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # --- 기사 목록 셀렉터 수정 ---
    # 동적 클래스에 덜 의존하도록 '최신 기사' heading 다음의 모든 <a> 태그를 찾아 필터링합니다.

    # 1단계: '최신 기사' <h3> 태그를 찾습니다. (이것은 고정 텍스트이므로 비교적 안정적)
    latest_news_heading = soup.find("h3", string="최신 기사") 
    
    potential_articles = []
    if latest_news_heading:
        # 2단계: '최신 기사' heading 바로 다음 형제 요소인 div (기사 리스트 컨테이너)를 찾습니다.
        # 이 div의 클래스명이 변하더라도 next_sibling으로 위치를 특정할 수 있습니다.
        news_list_container = latest_news_heading.find_next_sibling("div")
        
        if news_list_container:
            # 3단계: 컨테이너 안에서 모든 <a> 태그 (href 속성을 가진)를 찾습니다.
            # 이 방식은 'div.sc-53c9553f-0.ksjQKq'와 같은 동적 클래스에 의존하지 않습니다.
            potential_articles = news_list_container.find_all("a", href=True) 

    # DEBUG: 찾은 잠재적 기사 링크 개수를 출력해봅니다. (GitHub Actions 로그에서 확인)
    print(f"DEBUG: Found {len(potential_articles)} potential <a> tags.")
    
    # 4단계: 찾은 <a> 태그들 중에서 실제 기사 링크로 보이는 것만 필터링합니다.
    # 일반적으로 기사 링크는 특정 패턴을 가집니다 (예: /news/articleView.html?idxno=...)
    # 패션비즈의 기사 링크가 어떤 패턴을 가지는지 웹사이트에서 확인해봐야 합니다.
    # 여기서는 간단히 'articleView.html'을 포함하는 링크만 선택하도록 예시를 듭니다.
    articles = [
        a for a in potential_articles 
        if a.get('href') and ('articleView.html' in a['href'] or 'news/' in a['href'])
    ] # 실제 링크 패턴에 맞게 조정 필요

    if not articles:
        # 필터링 후에도 기사가 없다면 오류 발생
        raise Exception("패션비즈 웹사이트에서 기사를 찾을 수 없습니다. '최신 기사' 섹션 또는 기사 셀렉터/링크 패턴 확인 필요.")

    first_article = articles[0]
    
    # --- 제목 추출 ---
    # <a> 태그 내부에 <p class="tit"> 태그가 있는지 확인하고, 없으면 <a> 태그 전체 텍스트 사용
    title_element = first_article.select_one("p.tit")
    if title_element:
        title = title_element.get_text(strip=True)
    else:
        # p.tit이 없으면 <a> 태그의 모든 텍스트를 제목으로 간주
        title = first_article.get_text(strip=True)

    link = first_article['href']
    # 링크가 상대 경로일 경우 (예: /news/articleView.html?idxno=12345) 절대 경로로 변환
    if not link.startswith('http'):
        link = "https://www.fashionbiz.co.kr" + link
    
    print(f"DEBUG: Selected first article - Title: {title}, Link: {link}")

    # --- 기사 본문 셀렉터 ---
    # 이 부분은 여전히 직접 확인해야 합니다. 아래는 가장 흔한 예시입니다.
    # 실제 기사 페이지로 이동하여 본문 내용을 감싸는 정확한 태그/클래스/ID를 찾아야 합니다.
    article_response = requests.get(link)
    article_soup = BeautifulSoup(article_response.text, "html.parser")
    print(f"DEBUG: Fetching article content from: {link}")

    # 패션비즈 기사 본문 영역 셀렉터 (정확한 확인 필수!)
    content_element = article_soup.select_one("div#article-content") 
    if not content_element:
        content_element = article_soup.select_one("div.article_body_content") 
        if not content_element:
            content_element = article_soup.select_one("div.view_txt")
            if not content_element:
                content_element = article_soup.select_one("div.detail_view")
                if not content_element:
                    # 마지막으로, 가장 포괄적인 시도: <article> 태그나 본문처럼 보이는 div
                    content_element = article_soup.find("article") 
                    if not content_element:
                        content_element = article_soup.find("div", class_=lambda x: x and ('content' in x or 'body' in x))
                        if not content_element:
                            raise Exception(f"기사 본문 내용을 찾을 수 없습니다: {link}. 실제 기사 페이지의 셀렉터를 확인하세요.")

    content = content_element.get_text(strip=True)
    print(f"DEBUG: Article content successfully extracted (first 100 chars): {content[:100]}...")

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
