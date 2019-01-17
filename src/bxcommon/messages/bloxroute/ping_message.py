from bxcommon.messages.bloxroute.bloxroute_message_type import BloxrouteMessageType
from bxcommon.messages.bloxroute.keep_alive_message import KeepAliveMessage


class PingMessage(KeepAliveMessage):
    MESSAGE_TYPE = BloxrouteMessageType.PING

    def __init__(self, nonce=None, buf=None):
        KeepAliveMessage.__init__(self, msg_type=self.MESSAGE_TYPE, nonce=nonce, buf=buf)
