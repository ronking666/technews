import os
import requests
import yfinance as yf
from datetime import datetime

def get_market_data():
    """
    通过雅虎财经获取指数和金属的涨跌情况（增强版：防周末/节假日休市）
    """
    tickers = {
        "纳斯达克100指数": "^NDX",
        "黄金 (纽约期金)": "GC=F",
        "白银 (纽约期银)": "SI=F",
        "铜 (纽约期铜)": "HG=F",
        "铂金 (纽约期铂)": "PL=F",
        "稀土与战略金属ETF (代表稀有金属)": "REMX"
    }

    result_lines = []
    
    for name, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # 获取过去5天的数据，防止因为周末或节假日导致数据不足
            hist = ticker.history(period="5d")
            
            if len(hist) >= 2:
                # 永远取有效数据里的最后一天和倒数第二天
                prev_close = hist['Close'].iloc[-2]
                current = hist['Close'].iloc[-1]
                
                change = current - prev_close
                pct_change = (change / prev_close) * 100
                
                emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
                sign = "+" if change > 0 else ""
                
                result_lines.append(
                    f"### {name}\n"
                    f"> 最新价: **{current:.2f}** | 涨跌: {emoji} {sign}{change:.2f} ({sign}{pct_change:.2f}%)\n\n"
                    f"---\n"
                )
            else:
                result_lines.append(f"### {name}\n> 暂无最新数据（数据源获取异常）\n\n---\n")
        except Exception as e:
            result_lines.append(f"### {name}\n> 获取数据失败\n\n---\n")

    return "".join(result_lines)

def send_to_serverchan(sendkey, content):
    """
    推送到 Server酱
    """
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    today = datetime.now().strftime("%Y年%m月%d日")
    
    payload = {
        "title": f"📊 每日财经与金属行情早报 ({today})",
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
        
    print("开始获取市场数据...")
    market_content = get_market_data()
    
    print("准备推送...")
    send_to_serverchan(sendkey, market_content)
