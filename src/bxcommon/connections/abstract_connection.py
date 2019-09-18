import time
import traceback
import sys
from abc import ABCMeta
from collections import defaultdict
from typing import ClassVar, Generic, TypeVar, TYPE_CHECKING, Set, Optional

from bxcommon.messages.bloxroute.abstract_broadcast_message import AbstractBroadcastMessage
from bxutils import logging
from bxutils.logging.log_level import LogLevel
from bxutils.logging.log_record_type import LogRecordType

from bxcommon import constants
from bxcommon.connections.connection_state import ConnectionState
from bxcommon.connections.connection_type import ConnectionType
from bxcommon.exceptions import PayloadLenError
from bxcommon.messages.validation.default_message_validator import DefaultMessageValidator
from bxcommon.network.socket_connection import SocketConnection
from bxcommon.utils import convert
from bxcommon.utils.buffers.input_buffer import InputBuffer
from bxcommon.utils.buffers.message_tracker import MessageTracker
from bxcommon.utils.buffers.output_buffer import OutputBuffer
from bxcommon.utils.log_level import LogLevel
from bxcommon.utils.memory_utils import ObjectSize, SpecialMemoryProperties, SpecialTuple
from bxcommon.utils import memory_utils
from bxcommon.utils.stats import hooks
from bxcommon.utils.stats.direction import Direction
from bxcommon.models.outbound_peer_model import OutboundPeerModel

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from bxcommon.connections.abstract_node import AbstractNode

logger = logging.get_logger(__name__)
memory_logger = logging.get_logger(LogRecordType.BxMemory)
Node = TypeVar("Node", bound="AbstractNode")


class AbstractConnection(Generic[Node], SpecialMemoryProperties):
    __metaclass__ = ABCMeta

    CONNECTION_TYPE: ClassVar[ConnectionType] = ConnectionType.NONE
    node: Node

    def __init__(self, socket_connection, address, node: Node, from_me=False):
        if not isinstance(socket_connection, SocketConnection):
            raise ValueError("SocketConnection type is expected for socket_connection arg but was {0}."
                             .format(type(socket_connection)))

        self.socket_connection = socket_connection
        self.fileno = socket_connection.fileno()

        # (IP, Port) at time of socket creation.
        # If the version/hello message contains a different port (i.e. connection is not from me), this will
        # be updated to the one in the message.
        self.peer_ip, self.peer_port = address
        self.peer_id: Optional[str] = None
        self.external_ip = node.opts.external_ip
        self.external_port = node.opts.external_port

        self.from_me = from_me  # Whether or not I initiated the connection

        if node.opts.track_detailed_sent_messages:
            self.message_tracker = MessageTracker(self)
        self.outputbuf = OutputBuffer()
        self.inputbuf = InputBuffer()
        self.node = node

        self.state = ConnectionState.CONNECTING

        # Number of bad messages I've received in a row.
        self.num_bad_messages = 0
        self.peer_desc = "%s %d" % (self.peer_ip, self.peer_port)

        self.can_send_pings = False

        self.hello_messages = []
        self.header_size = 0
        self.message_factory = None
        self.message_handlers = None

        self.log_throughput = True

        self.ping_message = None
        self.pong_message = None
        self.ack_message = None

        # Default network number to network number of current node. But it can change after hello message is received
        self.network_num = node.network_num

        self.message_validator = DefaultMessageValidator()

        self._trace_message_tracker = defaultdict(int)
        self._last_trace_message_log_time = time.time()
        self.ping_interval_s: int = constants.PING_INTERVAL_S
        self.peer_model: Optional[OutboundPeerModel] = None
        logger.info("Initialized new connection: {}", self)

    def __repr__(self):
        return "Connection<type: {}, fileno: {}, address: {}, network_num: {}>".format(self.CONNECTION_TYPE,
                                                                                       self.fileno,
                                                                                       self.peer_desc,
                                                                                       self.network_num)

    def is_active(self):
        """
        Indicates whether the connection is established and not marked for close.
        """
        return self.state & ConnectionState.ESTABLISHED == ConnectionState.ESTABLISHED and \
               not self.state & ConnectionState.MARK_FOR_CLOSE

    def add_received_bytes(self, bytes_received):
        """
        Adds bytes received from socket connection to input buffer

        :param bytes_received: new bytes received from socket connection
        """
        assert not self.state & ConnectionState.MARK_FOR_CLOSE

        self.inputbuf.add_bytes(bytes_received)

    def get_bytes_to_send(self):
        assert not self.state & ConnectionState.MARK_FOR_CLOSE

        return self.outputbuf.get_buffer()

    def advance_sent_bytes(self, bytes_sent):
        self.advance_bytes_on_buffer(self.outputbuf, bytes_sent)
        if self.message_tracker:
            self.message_tracker.advance_bytes(bytes_sent)

    def enqueue_msg(self, msg, prepend=False):
        """
        Enqueues the contents of a Message instance, msg, to our outputbuf and attempts to send it if the underlying
        socket has room in the send buffer.

        :param msg: message
        :param prepend: if the message should be bumped to the front of the outputbuf
        """
        logger.log(msg.log_level(), "Enqueued message: {} on connection: {}", msg, self)

        if self.message_tracker:
            full_message = msg
        else:
            full_message = None
        self.enqueue_msg_bytes(msg.rawbytes(), prepend, full_message)

    def enqueue_msg_bytes(self, msg_bytes, prepend=False, full_message=None):
        """
        Enqueues the raw bytes of a message, msg_bytes, to our outputbuf and attempts to send it if the
        underlying socket has room in the send buffer.

        :param msg_bytes: message bytes
        :param prepend: if the message should be bumped to the front of the outputbuf
        :param full_message: full message for detailed logging
        """

        if self.state & ConnectionState.MARK_FOR_CLOSE:
            return

        size = len(msg_bytes)

        logger.debug("Enqueuing {} bytes on connection: {}", size, self)

        if prepend:
            self.outputbuf.prepend_msgbytes(msg_bytes)
            if self.message_tracker:
                self.message_tracker.prepend_message(len(msg_bytes), full_message)
        else:
            self.outputbuf.enqueue_msgbytes(msg_bytes)
            if self.message_tracker:
                self.message_tracker.append_message(len(msg_bytes), full_message)

        self.socket_connection.send()

    def pre_process_msg(self):
        is_full_msg, msg_type, payload_len = self.message_factory.get_message_header_preview_from_input_buffer(
            self.inputbuf)

        self.message_validator.validate(is_full_msg, msg_type, self.header_size, payload_len, self.inputbuf)
        # TODO: message validator does not pass on the new is_full_msg type onward to the stacktrace for recovery

        return is_full_msg, msg_type, payload_len

    def process_msg_type(self, message_type, is_full_msg, payload_len):
        """
        Processes messages that require changes to the regular message handling flow
        (pop off single message, process it, continue on with the stream)

        :param message_type: message type
        :param is_full_msg: flag indicating if full message is available on input buffer
        :param payload_len: length of payload
        :return:
        """

        pass

    def process_message(self):
        """
        Processes the next bytes on the socket's inputbuffer.
        Returns 0 in order to avoid being rescheduled if this was an alarm.
        """

        start_time = time.time()
        messages_processed = defaultdict(int)
        while True:
            if self.state & ConnectionState.MARK_FOR_CLOSE:
                return

            input_buffer_len_before = self.inputbuf.length
            is_full_msg = False
            payload_len = 0
            msg = None

            try:
                is_full_msg, msg_type, payload_len = self.pre_process_msg()

                self.process_msg_type(msg_type, is_full_msg, payload_len)

                if not is_full_msg:
                    break

                msg = self.pop_next_message(payload_len)

                # If there was some error in parsing this message, then continue the loop.
                if msg is None:
                    if self._report_bad_message():
                        return
                    continue

                # Full messages must be one of the handshake messages if the connection isn't established yet.
                if not (self.is_active()) \
                        and msg_type not in self.hello_messages:
                    logger.warning("Connection to {0} not established and got {1} message!  Closing.", self.peer_desc,
                                 msg_type)
                    self.mark_for_close()
                    return

                if self.log_throughput:
                    hooks.add_throughput_event(Direction.INBOUND, msg_type, len(msg.rawbytes()), self.peer_desc)

                if not logger.isEnabledFor(msg.log_level()) and logger.isEnabledFor(LogLevel.INFO):
                    self._trace_message_tracker[msg_type] += 1
                elif len(self._trace_message_tracker) > 0:
                    logger.info("Processed the following message types: {} on connection {} over {:.2f} seconds.",
                                self._trace_message_tracker, self, time.time() - self._last_trace_message_log_time)
                    self._trace_message_tracker.clear()
                    self._last_trace_message_log_time = time.time()

                logger.log(msg.log_level(), "Processing message: {} on connection: {}", msg, self)

                if msg_type in self.message_handlers:
                    msg_handler = self.message_handlers[msg_type]
                    msg_handler(msg)

                messages_processed[msg_type] += 1
                
                # TODO: only for debugging memory issues, should be removed!
                if memory_logger.isEnabledFor(LogLevel.INFO) and hasattr(msg, "buf"):
                    ref_count = sys.getrefcount(msg.buf)
                    if ref_count > 2:
                        extra_data = {}
                        if isinstance(msg, AbstractBroadcastMessage):
                            extra_data.update(
                                {
                                    "message_hash": msg.message_hash(),
                                    "message_id": msg.message_id(),
                                    "source_id": msg.source_id(),
                                    "network_num": msg.network_num()
                                }
                            )
                        memory_logger.info(
                            {
                                "type": "MessageBufferRefCountMismatch",
                                "ref_count": ref_count,
                                "msg_type": msg_type,
                                "buffer_len": len(msg.buf),
                                "payload_len": payload_len,
                                "extra_data": extra_data
                            }
                        )

            # TODO: Investigate possible solutions to recover from PayloadLenError errors
            except PayloadLenError as e:
                logger.error("ParseError on connection {}. Error: {}.", self, e.msg)
                self.mark_for_close()
                return

            except MemoryError as e:
                logger.error(
                    "Out of memory error occurred during message processing. Error: {}. Message bytes: {}. Trace: {}",
                    e, self._get_last_msg_bytes(msg, input_buffer_len_before, payload_len),
                    traceback.format_exc())
                raise

            # TODO: Throw custom exception for any errors that come from input that has not been validated and only catch that subclass of exceptions
            except Exception as e:

                # Attempt to recover connection by removing bad full message
                if is_full_msg:
                    logger.error(
                        "Message processing error. Trying to recover. Error: {}. Message bytes: {}. Trace: {}, Connection: {}",
                        e, self._get_last_msg_bytes(msg, input_buffer_len_before, payload_len),
                        traceback.format_exc(), self)

                    # give connection a chance to restore its state and get ready to process next message
                    self.clean_up_current_msg(payload_len, input_buffer_len_before == self.inputbuf.length)

                # Connection is unable to recover from message processing error if incomplete message is received
                else:
                    logger.error("Message processing error. Unable to recover. Error: {}. Message bytes: {}. Trace: {}",
                                 e, self._get_last_msg_bytes(msg, input_buffer_len_before, payload_len),
                                 traceback.format_exc())
                    self.mark_for_close(force_destroy_now=True)
                    return

                if self._report_bad_message():
                    return
            else:
                self.num_bad_messages = 0

        time_elapsed = time.time() - start_time
        if time_elapsed > constants.WARN_MESSAGE_PROCESSING_S:
            logger.info("Took {:.2f} seconds to process the following messages: {}. Connection: {}", time_elapsed,
                        messages_processed, self)

        logger.debug("Processed {} messages in {:.2f} seconds on connection: {}.", messages_processed, time_elapsed,
                     self)

    def pop_next_message(self, payload_len):
        """
        Pop the next message off of the buffer given the message length.
        Preserve invariant of self.inputbuf always containing the start of a valid message.

        :param payload_len: length of payload
        :return: message object
        """

        msg_len = self.message_factory.base_message_type.HEADER_LENGTH + payload_len
        msg_contents = self.inputbuf.remove_bytes(msg_len)
        return self.message_factory.create_message_from_buffer(msg_contents)

    def advance_bytes_on_buffer(self, buf, bytes_written):
        hooks.add_throughput_event(Direction.OUTBOUND, None, bytes_written, self.peer_desc)
        buf.advance_buffer(bytes_written)

    def send_ping(self):
        """
        Send a ping (and reschedule if called from alarm queue)
        """
        if self.can_send_pings and not self.state & ConnectionState.MARK_FOR_CLOSE:
            self.enqueue_msg(self.ping_message)
            return self.ping_interval_s
        return constants.CANCEL_ALARMS

    def msg_hello(self, msg):
        self.state |= ConnectionState.HELLO_RECVD
        if msg.node_id() is None:
            logger.warning("Hello message without peer_id received from {}".format(self))
        self.peer_id = msg.node_id()
        self.node.connection_pool.index_conn_node_id(self.peer_id, self)

        if len(self.node.connection_pool.get_by_node_id(self.peer_id)) > 1:
            if self.from_me:
                logger.info("Connection already exists for node id: {}. Closing connection: {}", self.peer_id, self)
                self.node.destroy_conn(self)
            return

        self.enqueue_msg(self.ack_message)

    def msg_ack(self, _msg):
        """
        Handle an Ack Message
        """
        self.state |= ConnectionState.HELLO_ACKD

    def msg_ping(self, msg):
        self.enqueue_msg(self.pong_message)

    def msg_pong(self, _msg):
        pass

    def mark_for_close(self, force_destroy_now=False):
        self.state |= ConnectionState.MARK_FOR_CLOSE

        if force_destroy_now:
            self.node.destroy_conn(self, retry_connection=True)

    def clean_up_current_msg(self, payload_len: int, msg_is_in_input_buffer: bool) -> None:
        """
        Removes current message from the input buffer and resets connection to a state ready to process next message.
        Called during the handling of message processing exceptions.

        :param payload_len: length of the payload of the currently processing message
        :param msg_is_in_input_buffer: flag indicating if message bytes are still in the input buffer
        :return:
        """

        if msg_is_in_input_buffer:
            self.inputbuf.remove_bytes(self.header_size + payload_len)

    def on_input_received(self) -> bool:
        """handles an input event from the event loop

        :return: True if the connection is receivable, otherwise False
        """
        return True

    def log_connection_mem_stats(self) -> None:
        """
        logs the connection's memory stats
        """
        class_name = self.__class__.__name__
        hooks.increment_obj_mem_stats(
            class_name,
            self.network_num,
            self.inputbuf,
            "input_buffer",
            ObjectSize("input_buffer", memory_utils.get_special_size(self.inputbuf).size, is_actual_size=True)
        )
        hooks.increment_obj_mem_stats(
            class_name,
            self.network_num,
            self.outputbuf,
            "output_buffer",
            ObjectSize("output_buffer", memory_utils.get_special_size(self.outputbuf).size, is_actual_size=True)
        )

    def update_model(self, model: OutboundPeerModel):
        logger.info("updated connection peer module {}", model)
        self.peer_model = model

    def _report_bad_message(self):
        """
        Increments counter for bad messages. Returns True if connection should be closed.
        :return: if connection should be closed
        """
        if self.num_bad_messages == constants.MAX_BAD_MESSAGES:
            logger.warning("Received too many bad messages. Closing connection: {}", self)
            self.mark_for_close()
            return True
        else:
            self.num_bad_messages += 1
            return False

    def _get_last_msg_bytes(self, msg, input_buffer_len_before, payload_len):

        if msg is not None:
            return convert.bytes_to_hex(msg.rawbytes()[:constants.MAX_LOGGED_BYTES_LEN])

        # bytes still available on input buffer
        if input_buffer_len_before == self.inputbuf.length:
            return convert.bytes_to_hex(
                self.inputbuf.peek_message(min(self.header_size + payload_len, constants.MAX_LOGGED_BYTES_LEN)))

        return "<not available>"

    def special_memory_size(self, ids: Optional[Set[int]] = None) -> SpecialTuple:
        return memory_utils.add_special_objects(self.inputbuf, self.outputbuf, ids=ids)
