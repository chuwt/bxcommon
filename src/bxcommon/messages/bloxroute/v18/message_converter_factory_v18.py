from bxcommon.messages.bloxroute.bloxroute_message_type import BloxrouteMessageType
from bxcommon.messages.bloxroute.v18.bdn_performance_stats_message_converter_v18 import \
    bdn_performance_stats_message_converter_v18
from bxcommon.messages.versioning.abstract_version_converter_factory import AbstractMessageConverterFactory
from bxcommon.messages.versioning.no_changes_message_converter import no_changes_message_converter


class _MessageConverterFactoryV18(AbstractMessageConverterFactory):
    _MESSAGE_CONVERTER_MAPPING = {
        BloxrouteMessageType.BDN_PERFORMANCE_STATS: bdn_performance_stats_message_converter_v18,
    }

    def get_message_converter(self, msg_type):
        if not msg_type:
            raise ValueError("msg_type is required.")

        if msg_type not in self._MESSAGE_CONVERTER_MAPPING:
            return no_changes_message_converter

        return self._MESSAGE_CONVERTER_MAPPING[msg_type]


message_converter_factory_v18 = _MessageConverterFactoryV18()
