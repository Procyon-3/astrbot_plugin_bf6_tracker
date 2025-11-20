# all_requests.py
"""接口文档：https://api.gametools.network/docs#/"""

__all__ = ['get_player_info', 'get_bf6_stats', 'get_bf_ban']
import aiohttp


async def get_player_info(name: str, platform: str = "pc") -> dict:
    base_url = 'https://api.gametools.network/bfglobal/player/?&skip_battlelog=false'
    url = f"{base_url}&name={name}&platform={platform}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if response.status != 200:
                response.raise_for_status()
            return data

async def get_bf6_stats(name: str, platform: str = "pc") -> dict:
    
    base_url = 'https://api.gametools.network/bf6/all/?format_values=false'
    url = f"{base_url}&platform={platform}&name={name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if response.status != 200:
                response.raise_for_status()
            return data

async def get_bf_ban(name: str, platform: str = "pc") -> dict:
    base_url = 'https://api.gametools.network/bfglobal/ban/'
    url = f"{base_url}?name={name}&platform={platform}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if response.status != 200:
                response.raise_for_status()
            return data


if __name__ == "__main__":
    pass