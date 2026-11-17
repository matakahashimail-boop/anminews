import os
import datetime
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

# 1. 集めたいニュースの検索キーワード
QUERIES = [
    ("子育て・教育", "子育て OR 育児 OR 保育"),
    ("心理学", "心理学 OR メンタルヘルス OR カウンセリング"),
    ("国際情勢（ウクライナ・イラン）", "ウクライナ 戦争 OR イラン 情勢"),
    ("国内政治", "国内政治 OR 国会 OR 政府 方針"),
    ("社会・福祉（虐待・DV）", "児童虐待 OR DV 対策 OR 支援"),
    ("フォーラム・イベント案内", "心理学 フォーラム OR 子育て シンポジウム OR DV 講演会")
]

def fetch_rss_items(query, max_items=4):
    encoded_q = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=ja&gl=JP&ceid=JP:ja"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    items = []
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            xml_data = res.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:max_items]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                items.append({"title": title, "link": link, "pubDate": pub_date})
    except Exception as e:
        print(f"Error fetching {query}: {e}")
    return items

def summarize_with_gemini(client, category, articles):
    if not articles:
        return []
    prompt = f"""
あなたはまゆさん専用の丁寧なニュースキュレーターです。
以下の「{category}」に関するニュース記事リストから、重要なものを最大3件選び、それぞれ3行の箇条書きで分かりやすく要約してください。
虐待やDV、戦争などの重たいニュースについては、過度に煽る表現を避け、事実を冷静かつ丁寧な言葉遣いでまとめてください。
フォーラムやイベント案内がある場合は、開催時期やテーマが分かるように整理してください。

出力は必ず以下のJSON配列形式のみにしてください。
[
  {{
    "title": "記事のタイトル",
    "link": "記事のURL",
    "importance": 4,
    "summary": ["箇条書き1点目", "箇条書き2点目", "箇条書き3点目"]
  }}
]

記事リスト:
{json.dumps(articles, ensure_ascii=False)}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    try:
        return json.loads(response.text)
    except Exception:
        return []

def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    jst = datetime.timezone(datetime.timedelta(hours=9))
    today_str = datetime.datetime.now(jst).strftime('%Y-%m-%d')
    
    all_sections_html = ""
    
    for category, query in QUERIES:
        raw_items = fetch_rss_items(query, max_items=5)
        summarized = summarize_with_gemini(client, category, raw_items)
        if not summarized:
            continue
            
        cards_html = ""
        for art in summarized:
            bullets = "".join([f"<li>{line}</li>" for line in art.get("summary", [])])
            imp = art.get("importance", 3)
            cards_html += f"""
            <article class="card">
                <div class="meta">
                    <span class="badge">{category}</span>
                    <span class="imp">重要度 {imp}</span>
                </div>
                <h3><a href="{art['link']}" target="_blank" rel="noopener noreferrer">{art['title']}</a></h3>
                <details open>
                    <summary>要約を読む</summary>
                    <ul>{bullets}</ul>
                </details>
            </article>
            """
        all_sections_html += f"""
        <section>
            <h2>📌 {category}</h2>
            {cards_html}
        </section>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>まゆのAIニュースノート</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 24px; }}
        h1 {{ font-size: 1.6rem; color: #2d3748; margin: 0; }}
        .date {{ color: #718096; font-size: 0.9rem; margin-top: 4px; }}
        h2 {{ font-size: 1.2rem; color: #4a5568; border-left: 4px solid #667eea; padding-left: 10px; margin-top: 32px; }}
        .card {{ background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }}
        .meta {{ font-size: 0.8rem; margin-bottom: 8px; display: flex; gap: 8px; align-items: center; }}
        .badge {{ background: #ebf4ff; color: #4c51bf; padding: 2px 8px; border-radius: 999px; font-weight: bold; }}
        .imp {{ color: #718096; }}
        h3 {{ font-size: 1.05rem; margin: 0 0 10px 0; }}
        h3 a {{ color: #2b6cb0; text-decoration: none; }}
        h3 a:hover {{ text-decoration: underline; }}
        summary {{ cursor: pointer; font-size: 0.85rem; color: #718096; font-weight: bold; }}
        ul {{ margin: 8px 0 0 0; padding-left: 20px; font-size: 0.95rem; color: #4a5568; }}
        li {{ margin-bottom: 4px; }}
    </style>
</head>
<body>
    <header>
        <h1>📰 まゆのAIニュースノート</h1>
        <div class="date">最終更新: {today_str}</div>
    </header>
    <main>
        {all_sections_html}
    </main>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
