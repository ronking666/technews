# 全球科技新闻来源扩展设计

## 背景

2026 年 8 月 1 日科技早报没有覆盖 7 月 31 日发布的
DeepSeek-V4-Flash-0731 更新。该更新主要出现在 DeepSeek 官方变更日志和
Hacker News 讨论中，而项目当前只配置了 IT之家、少数派、爱范儿三个中文综合
RSS，每个来源取最新 8 条，因此对全球 AI、开发者社区和海外科技媒体的覆盖不足。

## 目标

- 保留现有三个来源的名称、URL、顺序和抓取数量，不修改既有行为。
- 在配置末尾追加能覆盖全球重要科技、AI、研究与公司官方发布的 RSS。
- 所有新增来源必须能被项目现有 RSS 解析器直接读取，不引入新依赖或适配器。
- 保持早报长度在现有 DeepSeek 摘要的 12000 字符输入上限内。
- 单个新增来源失败时，继续发送其他来源内容。

## 方案比较

### 方案 A：只增加公司官方 RSS

优点是发布信息最直接；缺点是需要为大量公司分别配置来源，仍会遗漏没有 RSS 的
公司（例如 Anthropic），并使报告明显变长。

### 方案 B：只增加聚合媒体

优点是来源少、覆盖广；缺点是公司更新可能延迟，安静发布的技术变更仍可能漏掉。

### 方案 C：社区、专业媒体和官方源组合（采用）

追加以下六个来源：

1. Hacker News 热门：捕捉开发者社区中的早期技术发布和安静更新。
2. Ars Technica：覆盖全球技术、科学、安全和产业新闻。
3. TechCrunch AI：覆盖全球 AI 公司、产品和融资动态。
4. MIT Technology Review AI：覆盖 AI 研究、政策与前沿趋势。
5. OpenAI 官方动态：直接覆盖 OpenAI 产品和研究发布。
6. Google AI 官方动态：直接覆盖 Google/Gemini 产品和研究发布。

该组合兼顾早期信号、独立媒体和一手发布。真实抓取验证中，九个来源共 72 条新闻，
渲染报告约 9715 字符，低于现有 12000 字符 AI 输入上限。

## 配置变更

只在 `config.toml` 现有第三个 `[[news.sources]]` 后追加六个表项：

| 名称 | RSS URL |
| --- | --- |
| Hacker News 热门 | `https://hnrss.org/frontpage` |
| Ars Technica | `https://feeds.arstechnica.com/arstechnica/index` |
| TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/feed/` |
| MIT Technology Review AI | `https://www.technologyreview.com/topic/artificial-intelligence/feed/` |
| OpenAI 官方动态 | `https://openai.com/news/rss.xml` |
| Google AI 官方动态 | `https://blog.google/technology/ai/rss/` |

不修改 `items_per_source`、`deduplicate`、`keywords`、已有来源或工作流调度。

## 测试与验收

- 配置测试精确断言原三个来源仍是列表前缀且值不变。
- 配置测试断言六个新增来源及 URL 全部存在。
- 继续要求所有来源域名互不重复。
- 使用项目现有 `fetch_news_source` 对六个新增 URL 做真实只读抓取，确认均能返回条目。
- 运行完整 pytest、Ruff、格式、编译和敏感信息检查。
- 不触发科技早报或财经早报手动工作流，不消耗 Server酱额度。

## 失败处理

沿用现有隔离策略：任何新增来源暂时不可用时，仅在该来源区块显示“获取失败”，
其他来源和整份早报继续发送。
