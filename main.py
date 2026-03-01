import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def get_tech_news():
    """
    通过解析 IT之家 (ITHome) 的官方 RSS 源获取最新科技资讯。
    直接请求官方源，最稳定，不易失效。
    """
    url = "https://www.ithome.com/rss/"
    try:
        # 伪装成普通浏览器，防止被盾拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 使用 Python 自带的 XML 库解析 RSS 数据
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        if not items:
            return "获取资讯失败：源网站未返回数据。"

        news_list = []
        
        # 提取前 12 条最新资讯
        for index, item in enumerate(items[:12], 1):
            title = item.find('title').text if item.find('title') is not None else '无标题'
            link = item.find('link').text if item.find('link') is not None else ''
            
            # 格式化为带有超链接的 Markdown
            if link:
                news_list.append(f"### {index}. [{title}]({link})\n\n---\n")
            else:
                news_list.append(f"### {index}. {title}\n\n---\n")
        
        return "".join(news_list)
        
    except Exception as e:
        return f"抓取资讯时发生异常：{e}"

def send_to_serverchan(sendkey, content):
    """
    推送到 Server酱
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    today = datetime.now().strftime("%Y年%m月%d日")
    
    payload = {
        "title": f"📰 每日科技资讯早报 ({today})",
        "desp": content
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("code") == 0:
            print("✅ 成功推送到微信！")
        else:
            print(f"❌ 推送失败，Server酱返回信息：{result}")
    except Exception as e:
        print(f"❌ 请求 Server酱 接口时发生异常：{e}")

if __name__ == "__main__":
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        print("错误：未找到 SERVERCHAN_SENDKEY 环境变量。")
        exit(1)
        
    print("开始获取最新科技资讯...")
    news_content = get_tech_news()
    
    print("准备推送...")
    send_to_serverchan(sendkey, news_content)
