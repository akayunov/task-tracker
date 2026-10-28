"""Block until PostgreSQL accepts connections with the application credentials."""

import asyncio
import os
import sys

import asyncpg


def _dsn() -> str:
    url = os.environ['DATABASE_URL']
    prefix = 'postgresql+asyncpg://'
    if url.startswith(prefix):
        return 'postgresql://' + url[len(prefix) :]
    return url


async def _wait() -> None:
    dsn = _dsn()
    for attempt in range(1, 31):
        try:
            connection = await asyncpg.connect(dsn)
        except (OSError, asyncpg.PostgresError):
            print(f'database is not ready (attempt {attempt})', flush=True)
            await asyncio.sleep(1)
            continue
        await connection.close()
        print('database is ready', flush=True)
        return
    print('database did not become ready in time', file=sys.stderr)
    sys.exit(1)


def main() -> None:
    asyncio.run(_wait())


if __name__ == '__main__':
    main()
