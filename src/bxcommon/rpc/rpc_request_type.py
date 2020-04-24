from bxcommon.models.serializeable_enum import SerializeableEnum


class RpcRequestType(SerializeableEnum):
    BLXR_TX = 0
    GATEWAY_STATUS = 1
    STOP = 2
    MEMORY = 3
    PEERS = 4
    BDN_PERFORMANCE = 5
    HEALTHCHECK = 6
