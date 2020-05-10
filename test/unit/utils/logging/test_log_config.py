from bxcommon.test_utils.abstract_test_case import AbstractTestCase
from logging import Formatter, LogRecord, StreamHandler
from bxutils import logging
from bxutils.logging import handler_type
from bxutils.logging import log_config
from bxutils.logging import log_format
from bxutils import log_messages
from bxutils.logging import log_format
from aiofluent.handler import FluentHandler
import json

import unittest


class JsonFormatterTesting(AbstractTestCase):
    def setUp(self) -> None:
        pass

    def _get_handlers(self, logger):
        handlers = []
        while logger.hasHandlers():
            handlers.extend(logger.handlers)
            if logger.propagate:
                logger = logger.parent
            else:
                break
        return handlers

    def test_create_logger(self):
        log_config.setup_logging(
            log_format=log_config.LogFormat.JSON,
            default_log_level=log_config.LogLevel.TRACE,
            default_logger_names="",
            log_level_overrides={}
        )

        logger = logging.get_logger("test_logging")
        handlers = self._get_handlers(logger)
        self.assertEqual(len(handlers), 1)
        for handler in handlers:
            self.assertIsInstance(handler, StreamHandler)
            self.assertIsInstance(handler.formatter, log_format.JSONFormatter)

    def test_create_logger_fluentd(self):
        log_config.setup_logging(
            log_format=log_config.LogFormat.JSON,
            default_log_level=log_config.LogLevel.TRACE,
            default_logger_names="",
            log_level_overrides={},
            enable_fluent_logger=True,
            fluentd_host="fluentd"
        )
        logger = logging.get_logger("test_logging")
        handlers = self._get_handlers(logger)
        self.assertEqual(len(handlers), 2)
        stream_handlers = [handler for handler in handlers if isinstance(handler, StreamHandler)]
        fluentd_handlers = [handler for handler in handlers if isinstance(handler, FluentHandler)]
        self.assertEqual(len(stream_handlers), 1)
        self.assertEqual(len(fluentd_handlers), 1)
        for handler in handlers:
            self.assertEqual(handler.level, 0)

        fluentd_handler = fluentd_handlers[0]
        stream_handler = stream_handlers[0]
        self.assertIsInstance(fluentd_handler.formatter, log_format.JSONFormatter)
        self.assertIsInstance(stream_handler.formatter, log_format.JSONFormatter)

    def test_custom_logger(self):
        log_config.setup_logging(
            log_format=log_config.LogFormat.JSON,
            default_log_level=log_config.LogLevel.TRACE,
            default_logger_names="",
            log_level_overrides={},
            enable_fluent_logger=True,
            fluentd_host="fluentd",
            third_party_loggers=[
                logging.LoggerConfig(
                    "test_logging", "{", logging.LogLevel.TRACE, handler_type.HandlerType.Fluent
                )]
        )
        logger = logging.get_logger("test_logging")
        handlers = self._get_handlers(logger)
        self.assertEqual(len(handlers), 1)
        stream_handlers = [handler for handler in handlers if isinstance(handler, StreamHandler)]
        fluentd_handlers = [handler for handler in handlers if isinstance(handler, FluentHandler)]
        self.assertEqual(len(stream_handlers), 0)
        self.assertEqual(len(fluentd_handlers), 1)
        for handler in handlers:
            self.assertEqual(handler.level, 0)

        fluentd_handler = fluentd_handlers[0]
        self.assertIsInstance(fluentd_handler.formatter, log_format.JSONFormatter)


if __name__ == '__main__':
    unittest.main()
