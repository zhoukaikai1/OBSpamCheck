import requests
import time
import os
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# =======================================
# 配置参数
# =======================================
#####需自行适配黑名单库##########
KEYWORDS = 黑名单库
DATE_LIMIT = '2026-03-14'  # 起始日期
SEARCH_URL = 'https://ask.oceanbase.com/search'
USER_URL = 'https://ask.oceanbase.com/u/{}.json'
MAX_WORKERS = 10
REQUEST_DELAY = 0.5
MAX_PAGES = 10



# 美观的ASCII艺术字
print("""
[周]  星河璀璨
███████╗ ██████╗ ██╗   ██╗██╗   ██╗███████╗
██╔════╝██╔═══██╗██║   ██║██║   ██║██╔════╝
█████╗  ██║   ██║██║   ██║██║   ██║███████╗
██╔══╝  ██║   ██║╚██╗ ██╔╝██║   ██║╚════██║
██║     ╚██████╔╝ ╚████╔╝ ╚██████╔╝███████║
╚═╝      ╚═════╝   ╚═══╝   ╚═════╝ ╚══════╝
多关键词论坛检索统计系统 v5.0——plus版
1.修复帖子最新评论不含水
2.对评论内容二次过滤，提升精度
3.对异常用户实行按人深度检索
4.日期自筛
5.多线程，增加并发性，加入锁
""")


HEADERS = {
    "accept": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# =======================================
# 日期循环：生成格式化日期关键词
# =======================================
today = datetime.now()
start_date = datetime.strptime(DATE_LIMIT, "%Y-%m-%d")
if start_date > today:
    raise ValueError(f"起始日期 {DATE_LIMIT} 大于当前日期 {today.strftime('%Y-%m-%d')}")

for i in range((today - start_date).days + 1):
    current_date = start_date + timedelta(days=i)
    formatted_date = f"{current_date.year}年{current_date.month}月{current_date.day}日"
    if formatted_date not in KEYWORDS:
        KEYWORDS.append(formatted_date)




# =======================================
# 主类：论坛分析器
# =======================================
class ForumAnalyzer:
    def __init__(self):
        self.post_ids = set()        # 评论ID去重
        self.topic_ids = set()       # 帖子ID去重
        self.user_count = defaultdict(int)  # 用户帖子数
        self.username_to_uid = {}
        self.uid_to_username = {}
        self.keyword_stats = defaultdict(int)
        self.user_keywords = defaultdict(set)
        self.post_details = []
        self.total_posts_fetched = 0
        self.user_comment_water_count = defaultdict(int)  # 评论级水次数
        self.user_topic_count = defaultdict(int)          # 水贴数（topic_id数量）
        self.lock = Lock()

    # =======================================
    # 获取用户评论级水次数
    # =======================================
    def get_user_water_comments(self, username, keywords, start_date_obj):
        URL = 'https://ask.oceanbase.com/user_actions.json'
        count = 0

        for offset in range(0, 300, 30):
            try:
                params = {"offset": offset, "username": username, "filter": "4,5"}
                response = requests.get(URL, params=params, headers=HEADERS, timeout=10)

                # ⭐ 请求计数加锁
                with self.lock:
                    self.total_posts_fetched += 1

                response.raise_for_status()
                data = response.json()
                need_continue = True

                for item in data.get("user_actions", []):
                    excerpt = item.get("excerpt", "")
                    time_str = item.get("created_at", "")
                    post_id = item.get("post_id")
                    action_type = item.get("action_type")
                    topic_id = item.get("topic_id")

                    if len(time_str) < 10:
                        continue

                    post_time = datetime.strptime(time_str[:10], "%Y-%m-%d")
                    if post_time < start_date_obj:
                        need_continue = False
                        break

                    matched_keywords = [k for k in keywords if k in excerpt]
                    if not matched_keywords:
                        continue

                    with self.lock:
                        if action_type == 5:
                            if post_id in self.post_ids:
                                continue
                            self.post_ids.add(post_id)
                            count += 1

                        elif action_type == 4:
                            if topic_id in self.topic_ids:
                                continue
                            self.topic_ids.add(topic_id)
                            self.user_topic_count[username] += 1
                            count += 1

                        # ⭐ 关键词统计
                        for k in matched_keywords:
                            self.keyword_stats[k] += 1

                        uid = self.username_to_uid.get(username)
                        if uid:
                            for k in matched_keywords:
                                self.user_keywords[uid].add(k)

                if not need_continue:
                    break

            except Exception as e:
                print(f"[用户行为分析失败] {username} - {e}")
                break

        return count

    # =======================================
    # 获取用户ID
    # =======================================
    def get_user_id(self, username):
        if username in self.username_to_uid:
            return self.username_to_uid[username]

        try:
            url = USER_URL.format(username)
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            uid = r.json().get('user', {}).get('id')
            if uid:
                self.username_to_uid[username] = uid
                self.uid_to_username[uid] = username
            time.sleep(REQUEST_DELAY)
            return uid
        except Exception as e:
            print(f"获取用户ID失败: {username} - {str(e)}")
            return None

    # =======================================
    # 搜索关键词
    # =======================================
    def search_keyword(self, keyword, page=1):
        params = {
            'q': f'{keyword} after:{DATE_LIMIT} status:public order:latest',
            'page': page
        }
        try:
            r = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"搜索失败: {keyword} 第{page}页 - {str(e)}")
            return None

    # =======================================
    # 处理帖子列表
    # =======================================
    def process_posts(self, keyword, posts):
        for topic in posts:

            # ⭐ 统计抓取量（加锁）
            with self.lock:
                self.total_posts_fetched += 1

            post_number = topic.get('post_number')
            blurb = topic.get('blurb', '') or ''
            if keyword not in blurb:
                continue

            topic_id = topic.get('topic_id') if post_number == 1 else None
            post_id = topic.get('id') if post_number != 1 else None

            username = topic['username']

            # ⭐ 去重 + 写入（必须整体加锁）
            with self.lock:
                if post_number == 1:
                    if topic_id in self.topic_ids:
                        continue
                    self.topic_ids.add(topic_id)
                    self.user_topic_count[username] += 1
                else:
                    if post_id in self.post_ids:
                        continue
                    self.post_ids.add(post_id)

                self.keyword_stats[keyword] += 1

            # 获取用户ID（不用锁）
            user_id = self.get_user_id(username)

            if user_id:
                with self.lock:
                    self.user_count[user_id] += 1
                    self.user_keywords[user_id].add(keyword)

            create_time = datetime.strptime(
                topic['created_at'],
                "%Y-%m-%dT%H:%M:%S.%f%z"
            ).strftime("%Y-%m-%d %H:%M:%S")

            print(f"[{keyword}] {create_time} | 用户: {username:<15} | ID: {user_id or 'N/A':<8} | "
                  f"{'帖子ID:' + str(topic_id) if post_number == 1 else '评论ID:' + str(post_id)}")

    # =======================================
    # 处理单个关键词
    # =======================================
    def process_keyword(self, keyword):
        page = 1
        while page <= MAX_PAGES:
            data = self.search_keyword(keyword, page)
            if not data or not data.get('posts'):
                break
            self.process_posts(keyword, data['posts'])
            page += 1
            time.sleep(REQUEST_DELAY)
        if page > MAX_PAGES:
            print(f"提示：关键词 '{keyword}' 已达到接口最大{MAX_PAGES}页限制，可能未统计全部数据")



    # =======================================
    # 运行分析
    # =======================================
    def run(self):
        start_time = time.time()

        # =======================================
        # 关键词抓取（多线程）
        # =======================================
        print("开始多线程关键词抓取...\n")

        def keyword_worker(keyword):
            try:
                self.process_keyword(keyword)
            except Exception as e:
                print(f"[关键词抓取失败] {keyword} - {e}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(keyword_worker, kw) for kw in KEYWORDS]
            for future in as_completed(futures):
                future.result()  # 确保异常抛出可见

        # =======================================
        # 二次统计：评论级复检（多线程，评论数>2）
        # =======================================
        print("\n开始进行用户评论级复检（多线程，评论数>2）...\n")
        start_date_obj = datetime.strptime(DATE_LIMIT, "%Y-%m-%d")

        def user_worker(uid, username):
            try:
                print(f"分析用户：{username}")
                comment_count = self.get_user_water_comments(username, KEYWORDS, start_date_obj)
                return uid, comment_count
            except Exception as e:
                print(f"[复检失败] 用户 {username} - {e}")
                return uid, 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for uid, post_cnt in self.user_count.items():
                if post_cnt < 2:  # 仅评论数>=2才复检
                    continue
                username = self.uid_to_username.get(uid)
                if username:
                    futures.append(executor.submit(user_worker, uid, username))

            for future in as_completed(futures):
                try:
                    uid, comment_count = future.result()
                    self.user_comment_water_count[uid] = comment_count
                except Exception as e:
                    print(f"[复检结果收集失败] {e}")

        # 输出最终结果
        self.display_results()
        print(f"\n总执行时间: {time.time() - start_time:.2f}秒")

    # =======================================
    # 输出结果
    # =======================================
    def display_results(self):
        print("\n" + "=" * 100)
        print("关键词出现统计:")
        for kw, cnt in self.keyword_stats.items():
            print(f"{kw:<8}: {cnt}次")

        print(f"\n{DATE_LIMIT}-今日用户黑榜度排名 (按总水数降序):")
        # print(
        #     f"{'用户ID':<10}\t{'用户名':<15}\t{'总水数':>6}\t{'关键词':<3}")

        print(
            f"{'用户ID':<10}\t{'用户名':<15}\t{'总水数':>6}\t{'评论数':<4}\t{'水贴数':<4}\t{'二次复检新增数':<4}\t{'关键词':<3}")
        print("-" * 100)

        # 计算每个用户的总水数
        user_total_water = {}
        for uid, post_cnt in self.user_count.items():
            username = self.uid_to_username.get(uid, '未知')
            comment_cnt = self.user_comment_water_count.get(uid, 0)
            water_post_count = self.user_topic_count.get(username, 0)
            total_sum = post_cnt + water_post_count + comment_cnt  # 总水数
            user_total_water[uid] = total_sum

        # 按总水数倒序排序
        for uid, total_sum in sorted(user_total_water.items(), key=lambda x: x[1], reverse=True):
            username = self.uid_to_username.get(uid, '未知')
            post_cnt = self.user_count.get(uid, 0)
            water_post_count = self.user_topic_count.get(username, 0)
            comment_cnt = self.user_comment_water_count.get(uid, 0)
            kws = ', '.join(sorted(self.user_keywords.get(uid, set())))
            # print(
            #     f"{uid:<10}\t{username:<20}\t{total_sum:>6}\t{kws}")

            print(
                f"{uid:<10}\t{username:<20}\t{total_sum:>6}\t{post_cnt:>6}\t{water_post_count:>6}\t{comment_cnt:>8}\t{kws}")

        print("\n" + "=" * 100)
        print(f"原始检索帖子总数（含重复）: {self.total_posts_fetched}")
        print(f"共检索到 {len(self.post_ids)} 个不重复帖子")
        print(f"涉及 {len(self.user_count)} 位不同用户")
        print(f"关键词覆盖率: {len(self.keyword_stats)}/{len(KEYWORDS)}")


# =======================================
# 主程序
# =======================================
if __name__ == '__main__':
    print(KEYWORDS)
    # input("回车开始362")
    analyzer = ForumAnalyzer()
    analyzer.run()

    # 防止Windows下窗口立即关闭
    if os.name == 'nt':
        os.system('pause')
    else:
        input("\n按Enter键退出...")
