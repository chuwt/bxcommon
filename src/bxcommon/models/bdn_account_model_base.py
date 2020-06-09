from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date

from bxcommon.models.bdn_service_model_config_base import BdnServiceModelConfigBase


@dataclass
class BdnAccountModelBase:
    account_id: str
    logical_account_name: str
    certificate: str
    # TODO change expire_date to datetime type
    expire_date: str = "1970-01-01"
    tx_free: Optional[BdnServiceModelConfigBase] = None
    tx_paid: BdnServiceModelConfigBase = BdnServiceModelConfigBase()
    block_paid: BdnServiceModelConfigBase = BdnServiceModelConfigBase()
    cloud_api: BdnServiceModelConfigBase = BdnServiceModelConfigBase()
    new_transaction_streaming: BdnServiceModelConfigBase = BdnServiceModelConfigBase()

    def is_account_valid(self) -> bool:
        today = datetime.utcnow().date()
        try:
            expire_date = date.fromisoformat(self.expire_date)
        except (KeyError, ValueError):
            return False

        return expire_date >= today
