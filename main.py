import os
import requests
from datetime import datetime

def get_tech_news():
    """
    通过 Readhub API 获取最新科技动态（比直接爬取网页更稳定）
    """
    url = "https://api.readhub.cn/topic"
    try:
        # 设置 timeout 防止请求卡死
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', [])
        
        if not data:
            return "今日暂无抓取到科技资讯。"

        # 提取前 10 条最新资讯
        news_list = []
        for index, item in enumerate(data[:10], 1):
            title = item.get('title', '无标题')
            summary = item.get('summary', '无摘要内容')
            # 截取摘要前150个字符，保持推送排版清爽
            if len(summary) > 150:
                summary = summary[:150] + "..."
            
            # 使用 Markdown 格式排版
            news_list.append(f"### {index}. {title}\n\n> {summary}\n\n---\n")
        
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
    # 从 GitHub Actions 环境变量中读取 SendKey
    sendkey = os.environ.get("SERVERCHAN_SENDKEY")
    if not sendkey:
        print("错误：未找到 SERVERCHAN_SENDKEY 环境变量，请检查 GitHub Secrets 配置。")
        exit(1)
        
    print("开始获取最新科技资讯...")
    news_content = get_tech_news()
    
    print("准备推送...")
    send_to_serverchan(sendkey, news_content)
