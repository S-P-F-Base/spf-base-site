from datetime import UTC, datetime, timedelta

from fastapi import Request
from jose import JWTError, jwt

from data_bases.log_db import LogDB, LogType
from data_bases.player_db import PlayerData, PlayerDB

from .config import Config


class PlayerSession:
    def __init__(self, request: Request):
        self.request = request
        self.token_data = self._decode_token()

    def _decode_token(self) -> dict | None:
        raw = self.request.cookies.get("session")
        if not raw:
            return None

        try:
            return jwt.decode(raw, Config.jwt_key(), algorithms=["HS256"])

        except JWTError:
            return None

    def get_discord_id(self) -> str | None:
        return self.token_data.get("discord_id") if self.token_data else None

    def get_steam_id(self) -> str | None:
        return self.token_data.get("steam_id") if self.token_data else None

    def get_player(self) -> PlayerData | None:
        steam_id = self.get_steam_id()
        discord_id = self.get_discord_id()

        player = None
        if steam_id:
            player = PlayerDB.get_pdata_steam(steam_id)
        if not player and discord_id:
            player = PlayerDB.get_pdata_discord(discord_id)

        return player[3] if player else None

    def create_token(self, discord_id: str | None, steam_id: str | None) -> str:
        payload = {
            "discord_id": discord_id or "",
            "steam_id": steam_id or "",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        return jwt.encode(payload, Config.jwt_key(), algorithm="HS256")

    def sync_with_discord(
        self,
        discord_id: str,
        discord_name: str,
        discord_avatar: str,
    ) -> PlayerData:
        existing_steam = self.get_steam_id()
        player = PlayerDB.get_pdata_discord(discord_id)

        if not player and existing_steam:
            player = PlayerDB.get_pdata_steam(existing_steam)
            if player:
                u_id, _, _, data = player
                data.discord_name = discord_name
                PlayerDB.update_player(
                    u_id, discord_id=discord_id, steam_id=existing_steam, data=data
                )
                LogDB.add_log(
                    LogType.PLAYER_UPDATE,
                    f"Player {u_id=} linked with Discord",
                    "Self",
                )
                return data

        elif player:
            return player[3]

        data = PlayerData(
            discord_name=discord_name,
            discord_avatar=discord_avatar,
        )
        PlayerDB.add_player(discord_id=discord_id, steam_id=None, data=data)
        LogDB.add_log(
            LogType.PLAYER_CREATED,
            f"Player {discord_id=} created via Discord",
            "Self",
        )
        return data

    def sync_with_steam(self, steam_id: str) -> PlayerData:
        existing_discord = self.get_discord_id()
        player = PlayerDB.get_pdata_steam(steam_id)

        if not player and existing_discord:
            player = PlayerDB.get_pdata_discord(existing_discord)
            if player:
                u_id, _, _, data = player
                PlayerDB.update_player(
                    u_id,
                    discord_id=existing_discord,
                    steam_id=steam_id,
                    data=data,
                )
                LogDB.add_log(
                    LogType.PLAYER_UPDATE,
                    f"Player {u_id=} linked with Steam",
                    "Self",
                )
                return data

        elif player:
            return player[3]

        data = PlayerData()
        PlayerDB.add_player(discord_id=None, steam_id=steam_id, data=data)
        LogDB.add_log(
            LogType.PLAYER_CREATED,
            f"Player {steam_id=} created via Steam",
            "Self",
        )
        return data
