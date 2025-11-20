import asyncio
from aiohttp import ClientResponseError
from all_requests import get_bf6_stats, get_bf_ban

# 简化的测试逻辑：复刻原插件的核心查询并用 print 输出
async def check_game_record_test(ea_name: str, platform: str = "pc"):
    data = {}
    ban = {}

    try:
        stat_task = asyncio.create_task(get_bf6_stats(ea_name, platform))
        ban_task = asyncio.create_task(get_bf_ban(ea_name))
        data = await stat_task
        ban = await ban_task
    except ClientResponseError as e:
        if e.status == 404:
            print(f"未找到 {platform} 平台，EA 名称为 {ea_name} 的战绩信息，请检查输入是否正确。")
            return
        else:
            print(f"请求战绩信息时发生错误，状态码：{e.status}，错误信息：{e.message}")
            return
    except Exception as e:
        print(f"请求战绩信息时发生未知错误：{e}")
        return

    # 封禁信息
    is_banned = ban.get("names", {}).get(ea_name, {}).get("hacker", False)

    bf6_stats = data or {}
    user_name = bf6_stats.get("userName", "N/A")
    kills = bf6_stats.get("kills", "0")
    deaths = bf6_stats.get("deaths", "0")
    match_wins = bf6_stats.get("wins", "0")
    match_losses = bf6_stats.get("loses", "0")

    # 游戏时间：转换为分钟
    time_played = int(parse_game_time(bf6_stats.get("timePlayed", "0 days, 0:00:00")).total_seconds() / 60)

    human_percentage = float(bf6_stats.get("humanPrecentage", "0"))
    human_kd = bf6_stats.get("infantryKillDeath", "0")
    human_kills = int(int(kills) * human_percentage / 100) if time_played else 0
    human_kills_per_minute = human_kills / time_played if time_played > 0 else 0

    win_rate = 0.0
    try:
        wins = float(match_wins)
        losses = float(match_losses)
        total = wins + losses
        if total > 0:
            win_rate = wins / total * 100
    except ValueError:
        pass

    ai_percentage = 100 - human_percentage

    print("""
战地6 战绩查询结果：
玩家名称：{user_name}
封禁状态：{ban_status}
总击杀数（含AI）：{kills}
总死亡数：{deaths}
AI率：{ai_percentage:.2f}%
真人击杀数：{human_kills}
真人KD：{human_kd}
真人每分钟击杀数：{human_kills_per_minute:.2f}
胜场数：{match_wins}
败场数：{match_losses}
胜率：{win_rate:.2f}%
游戏时间（分钟）：{time_played}
""".format(
        user_name=user_name,
        ban_status="已封禁" if is_banned else "未封禁",
        kills=kills,
        deaths=deaths,
        ai_percentage=ai_percentage,
        human_kills=human_kills,
        human_kd=human_kd,
        human_kills_per_minute=human_kills_per_minute,
        match_wins=match_wins,
        match_losses=match_losses,
        win_rate=win_rate,
        time_played=time_played,
    ))


def parse_game_time(time_str: str):
    from datetime import timedelta
    import re
    if not time_str:
        return timedelta(0)
    days = 0
    time_part = time_str

    if ',' in time_str:
        parts = time_str.split(',')
        day_match = re.search(r'(\d+)', parts[0])
        if day_match:
            days = int(day_match.group(1))
        if len(parts) > 1:
            time_part = parts[1]

    time_part = time_part.strip()
    h_m_s = time_part.split(':')
    if len(h_m_s) != 3:
        return timedelta(days=days)
    try:
        hours = int(h_m_s[0])
        minutes = int(h_m_s[1])
        seconds = int(h_m_s[2])
    except ValueError:
        return timedelta(days=days)

    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


async def main():
    # 在这里替换测试用 EA 名称和平台
    ea_name = "yuanzui814"  # 示例："Player123"
    platform = "pc"  # 可选："pc", "ps", "xbox" 等
    await check_game_record_test(ea_name, platform)

if __name__ == "__main__":
    asyncio.run(main())
