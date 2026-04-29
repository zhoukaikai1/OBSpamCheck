# OBSpamCheck Project Proposal

## 1. Project Name
OBSpamCheck

## 2. Project Introduction
OBSpamCheck is an open-source detection tool for OceanBase official community.
It can automatically crawl forum posts and comments, identify low-quality spam content such as daily check-in, meaningless replies and repetitive water posts, count the number of spam behaviors of community users, and output sorted user ranking results.

This tool helps community administrators quickly locate high-frequency watering users, reduce manual management costs, and maintain the high-quality content ecology of the OceanBase community.

## 3. Core Capabilities
- Multi-keyword spam content matching and identification
- Support custom date range interception statistics
- Multi-threaded high-efficiency data crawling analysis
- Deduplication statistics of topics and comments
- Generate user spam sorting list and keyword occupation statistics

## 4. Repository Address
https://github.com/zhoukaikai1/OBSpamCheck

## 5. Maintainer
zhoukaikai1


# OBSpamCheck 项目提案

## 一、项目名称
OBSpamCheck（OceanBase 社区灌水检测工具）

## 二、项目背景
OceanBase 官方论坛（ask.oceanbase.com）存在大量**签到、水评论、无意义灌水、刷积分**类内容，影响社区内容质量与阅读体验。
为了提升社区治理效率，自动识别高频灌水用户，辅助版主进行管理，特开发本工具。

## 三、项目目标
1. 自动扫描 OceanBase 社区的**灌水帖子、灌水评论**
2. 统计用户灌水行为，生成**灌水用户排行榜**
3. 支持按日期范围筛选、多关键词检索
4. 支持多线程并发抓取，提升检测效率
5. 去重统计，输出干净、可直接用于治理的用户名单

## 四、功能描述
OBSpamCheck 实现以下核心能力：

1. **多关键词灌水检测**
   - 黑名单库
   - 支持自动加入日期类关键词（2025年X月X日）

2. **双维度检测**
   - 主题帖（水主贴）
   - 评论回复（水评论）

3. **用户深度分析**
   - 自动获取用户 ID
   - 对高风险用户进行深度行为检索
   - 统计用户总灌水次数

4. **高效并发处理**
   - 多线程抓取
   - 请求加锁保证数据安全
   - 自动去重，避免重复统计

5. **可视化输出**
   - 输出用户黑榜排名
   - 展示总水数、评论数、水贴数、二次复检新增数
   - 展示命中关键词
   - 输出统计概览

## 五、实现方案
基于 Python 实现，核心技术：
- requests 进行接口请求
- 多线程 ThreadPoolExecutor 提升并发
- 线程锁保证数据安全
- 内置关键词库 + 日期自动扩展
- 自动去重（帖子ID / 评论ID）
- 支持自定义起始日期

## 六、使用方式
1. 配置检测起始日期
2. 运行脚本自动检索论坛内容
3. 自动输出灌水用户排名
4. 输出数据可直接用于社区治理

## 七、预期效果
1. 快速识别 OceanBase 社区灌水账号
2. 降低版主人工审核成本
3. 提升社区内容质量
4. 可长期运行，持续监控社区灌水行为

## 八、项目仓库地址
https://github.com/zhoukaikai1/OBSpamCheck

## 九、作者信息
GitHub：zhoukaikai1
功能：OceanBase 社区灌水检测、用户行为分析、黑榜生成工具
