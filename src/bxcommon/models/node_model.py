class NodeModel(object):
    def __init__(self, node_type=None, external_ip=None, external_port=None, network=None, online=None, node_id=None,
                 sid_start=None, sid_end=None, sid_expire_time=None, last_pong_time=None,
                 is_internal_miner=None, is_internal_gateway=None, source_version=None, protocol_version=None,
                 blockchain_network_num=None):
        self.external_port = external_port
        self.network = network
        self.online = online
        self.node_id = node_id
        self.sid_start = sid_start
        self.sid_end = sid_end
        self.sid_expire_time = sid_expire_time
        self.node_type = node_type
        self.external_ip = external_ip
        self.last_pong_time = last_pong_time
        self.is_internal_miner = is_internal_miner
        self.is_internal_gateway = is_internal_gateway
        self.source_version = source_version
        self.protocol_version = protocol_version
        self.blockchain_network_num = blockchain_network_num
