from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .all_requests import get_bf6_stats
from aiohttp import ClientResponseError

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

        try:
            data = await get_bf6_stats(ea_name, platform)
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
        
        # 处理并格式化战绩数据
        bf6_stats = data
        # 真人和AI合并统计
        user_name = bf6_stats.get("userName", "N/A")
        kills = bf6_stats.get("kills", "0") # 总击杀数，包括真人和AI
        deaths = bf6_stats.get("deaths", "0") # 总死亡数
        kills_per_minute = bf6_stats.get("killsPerMinute", "0") # 每分钟击杀数
        match_wins = bf6_stats.get("wins", "0") # 胜场数
        match_losses = bf6_stats.get("loses", "0") # 败场数
        time_played = int(self._parse_game_time(bf6_stats.get("timePlayed", "0 days, 0:00:00")).total_seconds() / 60) # 游戏时间，转换为timedelta对象再转化为分钟
        
        # 分开统计
        human_kd = bf6_stats.get("infantryKillDeath", "0") # 真人KD
        human_kills_float = (int(kills) * float(bf6_stats.get("humanPrecentage", "0")) / 100)
        human_kills = int(human_kills_float)  # 真人击杀数
        
        yield event.plain_result(
f"""
战地6 战绩查询结果：
玩家名称：{user_name}
总击杀数（含AI）：{kills}
总死亡数：{deaths}
每分钟击杀数（含AI）：{kills_per_minute}
胜场数：{match_wins}
败场数：{match_losses}
游戏时间（分钟）：{time_played}
真人击杀数：{human_kills}
真人KD：{human_kd}
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
    
