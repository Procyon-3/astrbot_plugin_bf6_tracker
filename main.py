from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .all_requests import get_bf6_stats, get_bf_ban
from aiohttp import ClientResponseError
import asyncio

class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 战地系列查战绩，暂时只支持bf6，仅限私聊和群聊，触发命令为“<平台命令前缀>查战绩 ea_name [游戏平台]”
    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE | filter.EventMessageType.GROUP_MESSAGE)
    @filter.command("查战绩")
    async def check_game_record(self, event: AstrMessageEvent, ea_name: str, platform: str = "pc"):
        """<平台命令前缀>查战绩 ea_name [游戏平台]"""
        data = {}
        ban = {}

        try:
            stat_task = asyncio.create_task(get_bf6_stats(ea_name, platform))
            ban_task = asyncio.create_task(get_bf_ban(ea_name))
            
            data = await stat_task
            ban = await ban_task
        except ClientResponseError as e:
            if e.status == 404:
                logger.info(f"接收到{e.status}状态码，未找到{platform}平台，EA名称为{ea_name}的战绩信息。")
                yield event.plain_result(f"未找到{platform}平台，EA名称为{ea_name}的战绩信息，请检查输入是否正确。")
                return
            else:
                logger.error(f"请求战绩信息时发生错误，状态码：{e.status}，错误信息：{e.message}")
                yield event.plain_result("请求战绩信息时发生错误，请稍后再试。")
                return
        except Exception as e:
            logger.error(f"请求战绩信息时发生未知错误：{e}")
            yield event.plain_result("发生未知错误")
            return
        
        # 封禁信息
        isbaned = ban.get("names", {}).get(ea_name, "{}").get("hacker", False)
        # 处理并格式化战绩数据
        bf6_stats = data
        # 真人和AI合并统计
        user_name = bf6_stats.get("userName", "N/A")
        kills = bf6_stats.get("kills", "0") 
        deaths = bf6_stats.get("deaths", "0") 
        kills_per_minute = bf6_stats.get("killsPerMinute", "0") 
        match_wins = bf6_stats.get("wins", "0") 
        match_losses = bf6_stats.get("loses", "0")
        # 游戏时间，转换为timedelta对象再转换
        time_played = self._parse_game_time(bf6_stats.get("timePlayed", "0 days, 0:00:00")).total_seconds()
        time_played_hour = self._parse_game_time(bf6_stats.get("timePlayed", "0 days, 0:00:00")).total_seconds() / 3600 if time_played > 0 else 0
        
        # 分开统计
        human_kd = bf6_stats.get("infantryKillDeath", "0")
        human_kills = int((int(kills) * float(bf6_stats.get("humanPrecentage", "0")) / 100)) if time_played else 0 # 容错
        human_kills_per_minute = float(human_kills) / (time_played / 60) if time_played > 0 else 0

        win_rate = float(match_wins) / (float(match_wins) + float(match_losses)) * 100 if (float(match_wins) + float(match_losses)) > 0 else "0.00"
        ai_percentage = 100 - float(bf6_stats.get("humanPrecentage", "0"))

        yield event.plain_result(
f"""
战地6 战绩查询结果：
玩家名称：{user_name}
封禁状态：{"已封禁" if isbaned else "未封禁"}
总击杀数（含AI）：{kills}
总死亡数：{deaths}
真人击杀数：{human_kills}
AI率：{ai_percentage:.2f}%
真人KD：{human_kd}
真人每分钟击杀数：{human_kills_per_minute:.2f}
胜场数：{match_wins}
败场数：{match_losses}
胜率：{win_rate:.2f}%
游戏时间（小时）：{time_played_hour:.1f}
""")
        event.stop_event()
        
            

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        pass

    # 处理返回的游戏时间字符串，转换为timedelta对象
    def _parse_game_time(self,time_str):
        from datetime import timedelta
        import re
        if not time_str:
             return timedelta(0)
        days = 0
        time_part = time_str

        # 1. 判断是否包含天数（通常包含逗号）
        if ',' in time_str:
            parts = time_str.split(',')
            # --- 解析天数部分 ---
            # parts[0] 可能为 "3 days", "1 day", "3day" 等
            # 使用正则提取数字
            day_match = re.search(r'(\d+)', parts[0])
            if day_match:
                days = int(day_match.group(1))
            
            # --- 获取时分秒部分 ---
            if len(parts) > 1:
                time_part = parts[1]
        
        # --- 解析时分秒部分 ---
        # time_part 是 "9:38:11" 或 " 9:38:11"
        time_part = time_part.strip()
        h_m_s = time_part.split(':')
    
        hours = int(h_m_s[0])
        minutes = int(h_m_s[1])
        seconds = int(h_m_s[2])
    
        # 2. 构建 timedelta 对象
        duration = timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
        )
    
        return duration
    
