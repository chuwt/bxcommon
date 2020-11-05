from typing import Dict, Any

from bxcommon.feed.feed import Feed
from bxcommon.feed.subscriber import Subscriber
from bxcommon.rpc.rpc_errors import RpcInvalidParams
from bxcommon.feed.eth.eth_transaction_feed_entry import EthTransactionFeedEntry
from bxcommon.feed.eth.eth_raw_transaction import EthRawTransaction
from bxcommon.feed.new_transaction_feed import FeedSource
from bxcommon.feed.eth import eth_filter_handlers
from bxutils import logging
from bxutils.logging.log_record_type import LogRecordType

logger = logging.get_logger()
logger_filters = logging.get_logger(LogRecordType.TransactionFiltering, __name__)


class EthNewTransactionFeed(Feed[EthTransactionFeedEntry, EthRawTransaction]):
    NAME = "newTxs"
    FIELDS = ["tx_hash", "tx_contents"]
    FILTERS = {"transaction_value_range_eth", "from", "to"}

    def __init__(self) -> None:
        super().__init__(self.NAME)

    def subscribe(self, options: Dict[str, Any]) -> Subscriber[EthTransactionFeedEntry]:
        include_from_blockchain = options.get("include_from_blockchain", None)
        if include_from_blockchain is not None:
            if not isinstance(include_from_blockchain, bool):
                raise RpcInvalidParams('"include_from_blockchain" must be a boolean')
        return super().subscribe(options)

    def publish(self, raw_message: EthRawTransaction) -> None:
        if not self.any_subscribers_want_item(raw_message):
            return
        super().publish(raw_message)

    def serialize(self, raw_message: EthRawTransaction) -> EthTransactionFeedEntry:
        return EthTransactionFeedEntry(raw_message.tx_hash, raw_message.tx_contents)

    def any_subscribers_want_item(self, raw_message: EthRawTransaction) -> bool:
        if raw_message.source == FeedSource.BLOCKCHAIN_SOCKET:
            for subscriber in self.subscribers.values():
                if subscriber.options.get("include_from_blockchain", True):
                    return True
            return False
        return True

    def should_publish_message_to_subscriber(
        self,
        subscriber: Subscriber[EthTransactionFeedEntry],
        raw_message: EthRawTransaction,
        serialized_message: EthTransactionFeedEntry,
    ) -> bool:
        if (
            raw_message.source == FeedSource.BLOCKCHAIN_SOCKET
            and not subscriber.options.get("include_from_blockchain", True)
        ):
            return False
        should_publish = True
        if subscriber.filters:
            logger_filters.trace(
                "checking if should publish to {} with filters {}",
                subscriber.subscription_id,
                subscriber.filters,
            )
            contents = serialized_message.tx_contents
            state = {
                "value": eth_filter_handlers.reformat_tx_value(contents["value"]),
                "to": contents["to"],
                "from": contents["from"],
            }
            should_publish = subscriber.validator(state)
            logger_filters.trace("should publish: {}", should_publish)
        return should_publish
