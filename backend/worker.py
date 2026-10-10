"""Optional local scheduler while n8n is unavailable; external send gate applies."""
import asyncio
from . import db
from .domain import tick
from .integrations import dispatch


async def main():
    db.migrate()
    while True:
        with db.connection() as c:
            tenants = [r[0] for r in c.execute('SELECT id FROM tenants')]
        for tenant in tenants:
            with db.connection() as c:
                tick(c, tenant)
            # Deliver only explicitly configured tenants.
            import os
            if tenant == os.getenv('MADAR_INTEGRATION_TENANT_ID'):
                await dispatch(tenant)
        await asyncio.sleep(300)


if __name__ == '__main__':
    asyncio.run(main())
