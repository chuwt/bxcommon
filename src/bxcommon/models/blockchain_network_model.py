class BlockchainNetworkModel(object):

    def __init__(self, protocol=None, network=None, network_num=None, type=None, environment=None,
                 default_attributes=None, block_interval=600, ignore_block_interval_count=3):
        self.protocol = protocol
        self.network = network
        self.network_num = network_num
        self.type = type
        self.environment = environment
        self.default_attributes = default_attributes

        # TODO: These values needs to come from SDN
        self.block_interval = block_interval
        self.ignore_block_interval_count = ignore_block_interval_count
        self.final_tx_confirmations_count = 6
        self.tx_contents_memory_limit_bytes = 200 * 1024 * 1024
