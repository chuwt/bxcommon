
CONTENT_TYPE_HEADER_KEY: str = "Content-Type"
PLAIN_HEADER_TYPE: str = "text/plain"
JSON_HEADER_TYPE: str = "application/json"
TRANSACTION_PARAMS_KEY: str = "transaction"
SYNCHRONOUS_PARAMS_KEY: str = "synchronous"
DETAILS_LEVEL_PARAMS_KEY: str = "details_level"
BLOCKCHAIN_PROTOCOL_PARAMS_KEY: str = "blockchain_protocol"
BLOCKCHAIN_NETWORK_PARAMS_KEY: str = "blockchain_network"
ACCOUNT_ID_PARAMS_KEY: str = "account_id"
AUTHORIZATION_HEADER_KEY: str = "Authorization"
RPC_SERVER_INIT_TIMEOUT_S: int = 10
RPC_SERVER_STOP_TIMEOUT_S: int = 10
HEALTHCHECK_INTERVAL = 60
DEFAULT_RPC_PORT: int = 28332
DEFAULT_RPC_HOST: str = "127.0.0.1"
DEFAULT_RPC_USER: str = ""
DEFAULT_RPC_PASSWORD: str = ""
MAINNET_NETWORK_NAME: str = "Mainnet"
CLOUD_API_URL: str = "https://api.bloxroute.com/{0}/blxr_transaction"  # TODO: confirm url

JSON_RPC_VERSION = "2.0"
JSON_RPC_REQUEST_ID = "id"
JSON_RPC_METHOD = "method"
JSON_RPC_PARAMS = "params"
JSON_RPC_VERSION_FIELD = "jsonrpc"
JSON_RPC_RESULT = "result"
JSON_RPC_ERROR = "error"
