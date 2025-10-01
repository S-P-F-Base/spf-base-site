import urllib.request

from data_control import Config


class GameDBProcessor:
    @classmethod
    def download_db(cls) -> None:
        urllib.request.urlretrieve(Config.game_server_ftp(), "data/game_server.db")

    @classmethod
    def cleanup_db(cls) -> None: ...

    @classmethod
    def delete_db(cls) -> None: ...
