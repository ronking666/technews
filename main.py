import os
import requests
from datetime import datetime

def get_tech_news():
    """
    通过免费的公开 API 获取最新IT科技动态 (韩小韩 API)
    """
    url = "https://api.vvhan.com/api/hotlist/itNews"
    try:
        # 加上 User-Agent 模拟真实浏览器，防止被拦截
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("success") or not result.get("data"):
            return "获取资讯失败，接口返回数据为空或正在维护中。"

        data = result.get('data', [])
        news_list = []
        
        # 提取前 10 条最新资讯
        for index, item in enumerate(data[:10], 1):
            title = item.get('title', '无标题')
            link = item.get('url', '')
            
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
