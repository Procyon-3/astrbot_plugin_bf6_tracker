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
        bf6_stats = {}
        ban = {}

        try:
            bf6_stats, ban = await asyncio.gather(
                get_bf6_stats(ea_name, platform),
                get_bf_ban(ea_name),
            )
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
        
        def _safe_int(value, default=0):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return default

        def _safe_float(value, default=0.0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        # 提取数据
        time_played_delta = self._parse_game_time(bf6_stats.get("timePlayed", "0 days, 0:00:00"))
        time_played_seconds = time_played_delta.total_seconds()
        time_played_hours = time_played_seconds / 3600 if time_played_seconds else 0

        kills = _safe_int(bf6_stats.get("kills"))
        deaths = _safe_int(bf6_stats.get("deaths"))
        human_percentage = _safe_float(bf6_stats.get("humanPrecentage"))
        match_wins = _safe_int(bf6_stats.get("wins"))
        match_losses = _safe_int(bf6_stats.get("loses"))
        total_matches = match_wins + match_losses

        # 真人击杀数 = 总击杀数 * 真人比例
        human_kills = int(kills * human_percentage / 100) if time_played_seconds else 0
        human_kills_per_minute = (human_kills / (time_played_seconds / 60)) if time_played_seconds else 0.0
        win_rate = (match_wins / total_matches * 100) if total_matches else 0.0
        ai_percentage = max(0.0, 100.0 - human_percentage)

        result = {
            "isbaned": ban.get("names", {}).get(ea_name, {}).get("hacker", False),
            "user_name": bf6_stats.get("userName", "N/A"),
            "kills": kills,
            "deaths": deaths,
            "kills_per_minute": _safe_float(bf6_stats.get("killsPerMinute")),
            "match_wins": match_wins,
            "match_losses": match_losses,
            "time_played": time_played_seconds,
            "time_played_hour": time_played_hours,
            "human_kd": bf6_stats.get("infantryKillDeath", "0"),
            "human_kills": human_kills,
            "human_kills_per_minute": human_kills_per_minute,
            "win_rate": win_rate,
            "ai_percentage": ai_percentage,
        }
        yield event.plain_result(
f"""
战地6 战绩查询结果：
玩家名称：{result.get("user_name", "N/A")}
封禁状态：{"已封禁" if result.get("isbaned", False) else "未封禁"}
总击杀数（含AI）：{result.get("kills", "0")}
总死亡数：{result.get("deaths", "0")}
真人击杀数：{result.get("human_kills", "0")}
AI率：{result.get("ai_percentage", 0):.2f}%
真人KD：{result.get("human_kd", "0")}
真人KPM：{result.get("human_kills_per_minute", 0):.2f}
胜场数：{result.get("match_wins", "0")}
败场数：{result.get("match_losses", "0")}
胜率：{result.get("win_rate", 0.0):.2f}%
游戏时间（小时）：{result.get("time_played_hour", 0):.1f}
""")
        event.stop_event()
        
            

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        pass

    # 处理返回的游戏时间字符串，转换为timedelta对象
    def _parse_game_time(self, time_str):
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

        if len(h_m_s) < 3:
            h_m_s += ["0"] * (3 - len(h_m_s))
        elif len(h_m_s) > 3:
            h_m_s = h_m_s[:3]

        try:
            hours = int(h_m_s[0])
            minutes = int(h_m_s[1])
            seconds = int(h_m_s[2])
        except ValueError:
            return timedelta(0)
    
        # 2. 构建 timedelta 对象
        duration = timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
        )
    
        return duration
    
