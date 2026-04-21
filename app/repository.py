from app.database import get_connection
from app.schemas import FavoriteServer


def list_favorites(telegram_user_id: int) -> list[FavoriteServer]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, label, host, created_at
            FROM favorite_servers
            WHERE telegram_user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (telegram_user_id,),
        ).fetchall()

    return [FavoriteServer(**dict(row)) for row in rows]


def save_favorite(telegram_user_id: int, label: str, host: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO favorite_servers (telegram_user_id, label, host)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_user_id, host)
            DO UPDATE SET label = excluded.label
            """,
            (telegram_user_id, label, host),
        )
        connection.commit()


def delete_favorite(telegram_user_id: int, host: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM favorite_servers
            WHERE telegram_user_id = ? AND host = ?
            """,
            (telegram_user_id, host),
        )
        connection.commit()
        return cursor.rowcount > 0
