from bxcommon.utils.message_buffer_builder import PayloadElement, PayloadBlock
from bxcommon.constants import NODE_ID_SIZE_IN_BYTES, HDR_COMMON_OFF
from bxcommon.messages.bloxroute.bloxroute_message_type import BloxrouteMessageType
from bxcommon.messages.bloxroute.version_message import VersionMessage
from bxcommon.utils import uuid_pack
from bxcommon.messages.bloxroute.protocol_version import PROTOCOL_VERSION


class HelloMessage(VersionMessage):
    """
    BloXroute relay hello message type.

    node_id: the id of the node

    """
    MESSAGE_TYPE = BloxrouteMessageType.HELLO
    HELLO_MESSAGE_BLOCK = PayloadBlock(VersionMessage.BASE_LENGTH, "HelloMessage", PROTOCOL_VERSION,
                                       PayloadElement(name="node_id", structure="%ss" % NODE_ID_SIZE_IN_BYTES,
                                                      encode=lambda x: uuid_pack.to_bytes(x),
                                                      decode=lambda x: uuid_pack.from_bytes(x))
                                       )
    HELLO_MESSAGE_LENGTH = VersionMessage.VERSION_MESSAGE_BLOCK.size + HELLO_MESSAGE_BLOCK.size

    def __init__(self, protocol_version=None, network_num=None, buf=None, node_id=None):
        if buf is None:
            buf = bytearray(HDR_COMMON_OFF + self.HELLO_MESSAGE_LENGTH)
            buf = self.HELLO_MESSAGE_BLOCK.build(buf, node_id=node_id)

        self.buf = buf
        self._node_id = None
        self._network_num = None
        self._memoryview = memoryview(buf)
        super(HelloMessage, self).__init__(self.MESSAGE_TYPE, self.HELLO_MESSAGE_LENGTH,
                                           protocol_version, network_num, buf)

    def __unpack(self):
        contents = self.HELLO_MESSAGE_BLOCK.read(self._memoryview)
        self._node_id = contents.get("node_id")

    def node_id(self):
        if self._node_id is None:
            self.__unpack()
        return self._node_id
