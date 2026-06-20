import json
import sys
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[1]
API_DIR = REPO_ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

from app.settings import get_settings  # noqa: E402
from app.store_factory import get_app_store  # noqa: E402


def main() -> None:
    settings = get_settings()
    tenant_id = UUID(settings.demo_tenant_id)
    tenant = get_app_store().seed_demo_data(tenant_id, settings.access_token_secret)
    print(
        json.dumps(
            {
                "tenant_id": str(tenant.id),
                "tenant_name": tenant.name,
                "store_backend": settings.store_backend,
                "seeded": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
