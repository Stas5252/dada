import logging
import uuid
from decimal import Decimal

from yookassa import Configuration, Payment

from app.settings import Settings

logger = logging.getLogger(__name__)

class YooKassaProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if settings.yookassa_shop_id and settings.yookassa_secret_key:
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("YooKassa is not configured (missing shop_id or secret_key).")

    def create_payment(
        self,
        amount_minor: int,
        currency: str,
        description: str,
        tenant_id: str,
        return_url: str | None = None,
    ) -> str | None:
        if not self.enabled:
            return None

        amount_major = Decimal(amount_minor) / 100
        amount_str = f"{amount_major:.2f}"

        return_url = return_url or f"{self.settings.api_public_url}/billing/success"
        
        idempotence_key = str(uuid.uuid4())
        
        try:
            payment = Payment.create({
                "amount": {
                    "value": amount_str,
                    "currency": currency
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "tenant_id": tenant_id
                }
            }, idempotence_key)
            
            if hasattr(payment, "confirmation") and hasattr(payment.confirmation, "confirmation_url"):
                return payment.confirmation.confirmation_url
            return None
        except Exception as e:
            logger.error(f"YooKassa create payment error: {e}")
            return None
