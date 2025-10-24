# Magic Values Migration Report
==================================================

Total magic values found: 1306

## Threshold Values (451)

- **app/core/contracts.py:65**
  - Value: `1`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MIN_LENGTH`

- **app/core/contracts.py:65**
  - Value: `20`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MAX_LENGTH`

- **app/core/contracts.py:107**
  - Value: `1`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MIN_LENGTH`

- **app/core/contracts.py:107**
  - Value: `20`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MAX_LENGTH`

- **app/core/contracts.py:141**
  - Value: `1`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MIN_LENGTH`

- **app/core/contracts.py:141**
  - Value: `20`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MAX_LENGTH`

- **app/core/contracts.py:173**
  - Value: `1`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MIN_LENGTH`

- **app/core/contracts.py:173**
  - Value: `20`
  - Context: `symbol: str = Field(..., min_length=1, max_length=20)`
  - Suggested config: `MAX_LENGTH`

- **app/models/optimization.py:158**
  - Value: `1`
  - Context: `parameters: List[OptimizationParameter] = Field(..., min_length=1, description="Parameters to optimize")`
  - Suggested config: `MIN_LENGTH`

- **app/exceptions/__init__.py:57**
  - Value: `100`
  - Context: `app.add_middleware(RateLimitingMiddleware, requests_per_minute=100)`
  - Suggested config: `REQUESTS_PER_MINUTE`

... and 441 more

## Percentage Values (130)

- **app/core/config.py:137**
  - Value: `0.02`
  - Context: `risk_free_rate: float = Field(`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:40**
  - Value: `0.1`
  - Context: `max_position_size: float = Field(default=0.1, description="Maximum position size (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:41**
  - Value: `0.01`
  - Context: `min_position_size: float = Field(default=0.01, description="Minimum position size (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:44**
  - Value: `0.05`
  - Context: `stop_loss_pct: float = Field(default=0.05, description="Stop loss percentage (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:45**
  - Value: `0.15`
  - Context: `take_profit_pct: float = Field(default=0.15, description="Take profit percentage (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:46**
  - Value: `0.05`
  - Context: `daily_loss_limit: float = Field(default=0.05, description="Daily loss limit (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:47**
  - Value: `0.15`
  - Context: `max_drawdown_limit: float = Field(default=0.15, description="Maximum drawdown limit (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:50**
  - Value: `0.8`
  - Context: `max_total_exposure: float = Field(default=0.8, description="Maximum total exposure (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:51**
  - Value: `0.3`
  - Context: `max_sector_exposure: float = Field(default=0.3, description="Maximum sector exposure (0-1)")`
  - Suggested config: `DEFAULT`

- **app/core/centralized_config.py:52**
  - Value: `0.7`
  - Context: `max_correlation: float = Field(default=0.7, description="Maximum correlation between positions")`
  - Suggested config: `DEFAULT`

... and 120 more

## Timeout Values (119)

- **app/services/paper_trading_service.py:59**
  - Value: `100`
  - Context: `default_config = PaperTradingConfig(`
  - Suggested config: `TIMEOUT_EXECUTION_DELAY_MS`

- **app/services/market_data_service.py:46**
  - Value: `5`
  - Context: `mock_config = DataFeedConfig(`
  - Suggested config: `TIMEOUT_TIMEOUT_SECONDS`

- **app/services/market_data_service.py:62**
  - Value: `30`
  - Context: `yahoo_config = DataFeedConfig(`
  - Suggested config: `TIMEOUT_TIMEOUT_SECONDS`

- **app/services/market_data_service.py:62**
  - Value: `2.0`
  - Context: `yahoo_config = DataFeedConfig(`
  - Suggested config: `TIMEOUT_RETRY_DELAY`

- **.venv/lib/python3.9/site-packages/aiohttp/connector.py:311**
  - Value: `15.0`
  - Context: `keepalive_timeout = 15.0`
  - Suggested config: `TIMEOUT_KEEPALIVE_TIMEOUT`

- **.venv/lib/python3.9/site-packages/mypyc/irbuild/statement.py:999**
  - Value: `True`
  - Context: `return emit_yield_from_or_await(builder, val, line, is_await=True)`
  - Suggested config: `IS_AWAIT`

- **.venv/lib/python3.9/site-packages/mypyc/irbuild/statement.py:1014**
  - Value: `False`
  - Context: `return emit_yield_from_or_await(builder, builder.accept(o.expr), o.line, is_await=False)`
  - Suggested config: `IS_AWAIT`

- **.venv/lib/python3.9/site-packages/mypyc/irbuild/statement.py:1018**
  - Value: `True`
  - Context: `return emit_yield_from_or_await(builder, builder.accept(o.expr), o.line, is_await=True)`
  - Suggested config: `IS_AWAIT`

- **.venv/lib/python3.9/site-packages/kombu/connection.py:135**
  - Value: `5`
  - Context: `connect_timeout = 5`
  - Suggested config: `TIMEOUT_CONNECT_TIMEOUT`

- **.venv/lib/python3.9/site-packages/kombu/common.py:183**
  - Value: `True`
  - Context: `for _ in eventloop(consumer.channel.connection.client,`
  - Suggested config: `TIMEOUT_IGNORE_TIMEOUTS`

... and 109 more

## Retry Values (29)

- **app/services/market_data_service.py:46**
  - Value: `3`
  - Context: `mock_config = DataFeedConfig(`
  - Suggested config: `RETRY_RETRY_ATTEMPTS`

- **app/services/market_data_service.py:62**
  - Value: `3`
  - Context: `yahoo_config = DataFeedConfig(`
  - Suggested config: `RETRY_RETRY_ATTEMPTS`

- **.venv/lib/python3.9/site-packages/aiohttp/client.py:797**
  - Value: `False`
  - Context: `retry_persistent_connection = False`
  - Suggested config: `RETRY_RETRY_PERSISTENT_CONNECTION`

- **.venv/lib/python3.9/site-packages/aiohttp/connector.py:677**
  - Value: `0`
  - Context: `attempts = 0`
  - Suggested config: `RETRY_ATTEMPTS`

- **.venv/lib/python3.9/site-packages/ecdsa/keys.py:1434**
  - Value: `0`
  - Context: `retry_gen = 0`
  - Suggested config: `RETRY_RETRY_GEN`

- **.venv/lib/python3.9/site-packages/kombu/pidbox.py:305**
  - Value: `True`
  - Context: `producer.publish(`
  - Suggested config: `RETRY_RETRY`

- **.venv/lib/python3.9/site-packages/kombu/pidbox.py:277**
  - Value: `True`
  - Context: `producer.publish(`
  - Suggested config: `RETRY_RETRY`

- **.venv/lib/python3.9/site-packages/asyncpg/connection.py:2068**
  - Value: `False`
  - Context: `return await self._do_execute(`
  - Suggested config: `RETRY_RETRY`

- **.venv/lib/python3.9/site-packages/redis/asyncio/cluster.py:699**
  - Value: `0`
  - Context: `retry_attempts = 0`
  - Suggested config: `RETRY_RETRY_ATTEMPTS`

- **.venv/lib/python3.9/site-packages/isort/main.py:1111**
  - Value: `False`
  - Context: `all_attempt_broken = False`
  - Suggested config: `RETRY_ALL_ATTEMPT_BROKEN`

... and 19 more

## Port Values (230)

- **app/main.py:189**
  - Value: `8000`
  - Context: `uvicorn.run(`
  - Suggested config: `PORT`

- **.venv/lib/python3.9/site-packages/aiohttp/_websocket/models.py:14**
  - Value: `1003`
  - Context: `UNSUPPORTED_DATA = 1003`
  - Suggested config: `UNSUPPORTED_DATA`

- **.venv/lib/python3.9/site-packages/pyasn1/codec/ber/decoder.py:163**
  - Value: `True`
  - Context: `supportConstructedForm = True`
  - Suggested config: `SUPPORTCONSTRUCTEDFORM`

- **.venv/lib/python3.9/site-packages/pyasn1/codec/ber/decoder.py:294**
  - Value: `True`
  - Context: `supportConstructedForm = True`
  - Suggested config: `SUPPORTCONSTRUCTEDFORM`

- **.venv/lib/python3.9/site-packages/pyasn1/codec/ber/decoder.py:1532**
  - Value: `True`
  - Context: `supportIndefLength = True`
  - Suggested config: `SUPPORTINDEFLENGTH`

- **.venv/lib/python3.9/site-packages/pyasn1/codec/ber/encoder.py:26**
  - Value: `True`
  - Context: `supportIndefLenMode = True`
  - Suggested config: `SUPPORTINDEFLENMODE`

- **.venv/lib/python3.9/site-packages/mypyc/codegen/emitclass.py:181**
  - Value: `True`
  - Context: `context.declarations[name] = HeaderDeclaration(`
  - Suggested config: `NEEDS_EXPORT`

- **.venv/lib/python3.9/site-packages/mypyc/codegen/emitclass.py:192**
  - Value: `True`
  - Context: `context.declarations[emitter.native_function_name(cl.ctor)] = HeaderDeclaration(`
  - Suggested config: `NEEDS_EXPORT`

- **.venv/lib/python3.9/site-packages/mypyc/codegen/emitmodule.py:440**
  - Value: `True`
  - Context: `emitter.context.declarations[emitter.native_function_name(fn.decl)] = HeaderDeclaration(`
  - Suggested config: `NEEDS_EXPORT`

- **.venv/lib/python3.9/site-packages/mypyc/codegen/emitmodule.py:1052**
  - Value: `True`
  - Context: `emitter.context.declarations[static_name] = HeaderDeclaration(`
  - Suggested config: `NEEDS_EXPORT`

... and 220 more

## Size Values (347)

- **app/services/signal_scorer.py:236**
  - Value: `0`
  - Context: `removed_count = 0`
  - Suggested config: `REMOVED_COUNT`

- **app/services/parameter_optimization_service.py:47**
  - Value: `0`
  - Context: `self.optimization_summary = OptimizationSummary(`
  - Suggested config: `ARTIFACTS_COUNT`

- **.venv/lib/python3.9/site-packages/pycodestyle.py:96**
  - Value: `4`
  - Context: `INDENT_SIZE = 4`
  - Suggested config: `INDENT_SIZE`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3191**
  - Value: `False`
  - Context: `default_encountered = False`
  - Suggested config: `DEFAULT_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3194**
  - Value: `False`
  - Context: `type_var_tuple_encountered = False`
  - Suggested config: `TYPE_VAR_TUPLE_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3241**
  - Value: `False`
  - Context: `default_encountered = False`
  - Suggested config: `DEFAULT_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3244**
  - Value: `False`
  - Context: `type_var_tuple_encountered = False`
  - Suggested config: `TYPE_VAR_TUPLE_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3672**
  - Value: `False`
  - Context: `default_value_encountered = False`
  - Suggested config: `DEFAULT_VALUE_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3198**
  - Value: `True`
  - Context: `type_var_tuple_encountered = True`
  - Suggested config: `TYPE_VAR_TUPLE_ENCOUNTERED`

- **.venv/lib/python3.9/site-packages/typing_extensions.py:3689**
  - Value: `True`
  - Context: `default_value_encountered = True`
  - Suggested config: `DEFAULT_VALUE_ENCOUNTERED`

... and 337 more


## Configuration Additions
==============================

Add these to your .env file:

# Additional configuration from magic values migration

ADMIN__SHA256_CRYPT__MIN_ROUNDS=1024000
ADMIN__SHA512_CRYPT__MIN_ROUNDS=1024000
ALL_COUNT=0
ALWAYS_INCLUDE_PORT=True
AMQP_PORT=5672
ANY_COUNT=0
ARGSREPR_MAXSIZE=1024
ARG_COUNT=0
ARTIFACTS_COUNT=0
BACKOFF_FACTOR=0.25
BACKOFF_MAX=120
BIG5_TABLE_SIZE=5376
BIG5_TYPICAL_DISTRIBUTION_RATIO=0.75
BITCOUNT=0
BLOCKSIZE=8192
BLOCK_SIZE=64
BUFSIZE=0
CALC_QUEUE_SIZE=True
CALL_COUNT=0
CAN_CACHE_DECLARATION=False
CAN_CLOSE_OR_TERMINATE_CONNECTION=True
CAPPED_QUEUE_SIZE=100000
CHANNEL_MAX=65535
CHECKSUM_SIZE=40
CHECK_PREIMPORTED=True
CHECK_SUPPORTED_WHEELS=True
CHORD_SIZE=0
CHUNKSIZE=0
CHUNK_SIZE=8192
CIMPORTS=True
CIMPORT_STATEMENT=True
CLIENT_MAX_WINDOW_BITS=12
CLS_COUNTER=0
COERCE_NUMBERS_TO_STR=False
COLUMN_NUMBER=0
CONTAINS_IMPORTS=True
CONTENT_LENGTH_MAX_DIGITS=20
COUNT=0
COUNTED_BINDPARAM=0
COUNTER=0
CURRENT_VALUE=0.5
DEFAULT=0.02
DEFAULT_BASE=0.008
DEFAULT_BULK_MAX_MESSAGES=32
DEFAULT_CAP=0.512
DEFAULT_CONNECTION_WAIT_TIME_SECONDS=5
DEFAULT_ENCOUNTERED=False
DEFAULT_EXPIRATION_SECONDS=86400
DEFAULT_MAX_INTERVAL=2
DEFAULT_MAX_REDIRECTS=20
DEFAULT_MAX_SIZE=10000
DEFAULT_POOLSIZE=10
DEFAULT_PORT=9092
DEFAULT_SALT_SIZE=12
DEFAULT_SSL_PORT=5671
DEFAULT_VALUE_ENCOUNTERED=False
DEFAULT_WAIT_TIME_SECONDS=5
DETERMINISTIC_ORDER=True
DIGESTSIZE=16
DIGEST_SIZE=20
DLLEXPORT=True
DL_BLOCKSIZE=8192
DOT_COUNT=0
DURATION_DAYS=1
ELF_MAGIC_NUMBER=2135247942
ENABLE_VIRTUAL_TERMINAL_INPUT=512
ENABLE_VIRTUAL_TERMINAL_PROCESSING=4
ENCOUNTERED_PARTIAL_TYPE=False
EQUALCOUNT=0
ERRORCOUNT=0
ERROR_COUNT=3
ERROR_OPERATION_ABORTED=995
ES_MAX_RETRIES=3
EUCKR_TABLE_SIZE=2352
EUCKR_TYPICAL_DISTRIBUTION_RATIO=6.0
EUCTW_TABLE_SIZE=5376
EUCTW_TYPICAL_DISTRIBUTION_RATIO=0.75
EVENT_COUNT=0
EXCLUDE_MAX=False
EXCLUDE_MIN=False
EXPLICIT_MIN_ROUNDS=False
FILL_SIZE=4
FINAL_ITERATION=False
FINAL_SIZE=0
FIXEDCHUNKSIZE=0
GB2312_TABLE_SIZE=3760
GB2312_TYPICAL_DISTRIBUTION_RATIO=0.9
GE=0.0001
HAS_TERMINATE=True
HEARTBEAT_DRIFT_MAX=16
HEARTBEAT_MAX=4
HIGHEST_COUNT=0
HOST_COUNT=0
HTTP_208_ALREADY_REPORTED=208
HTTP_415_UNSUPPORTED_MEDIA_TYPE=415
HTTP_505_HTTP_VERSION_NOT_SUPPORTED=505
INCLUSIVE_MAX=False
INCLUSIVE_MIN=False
INDENT_SIZE=4
INFERRED_DEPTH=1.0
INNERLOOPCOUNTER=0
INSERTMANYVALUES_MAX_PARAMETERS=2099
IS_AWAIT=True
IS_NUMBER=False
IS_REEXPORT=True
IS_REFCOUNTED=True
ITEM_COUNT=0
ITERATION=0
ITERATIONS=0
ITERATIONS_COMPLETED=2
ITER_CHUNK_SIZE=512
JIS_TABLE_SIZE=4368
JIS_TYPICAL_DISTRIBUTION_RATIO=3.0
KEY_SIZE=64
KTLSPROTOCOLMAXSUPPORTED=999
KWARGSREPR_MAXSIZE=1024
LCOUNT=0
LE=1.0
LINES_AFTER_IMPORTS=1
LINES_BEFORE_IMPORTS=1
LINE_COUNT=1
LOCALS_MAX_LENGTH=10
LOCALS_MAX_STRING=80
LOG2_SIZE=17
LONG_STRING_MIN_LEN=64
LOOP_COUNT=0
MAGIC_NUMBER=10
MATCH_COUNT=0
MAX=1
MAXCHUNKSIZE=1000
MAXFDS_TO_SEND=256
MAXHEADERLEN=0
MAXLEN=100
MAXLINELEN=65
MAXNUMBEROFMESSAGES=1
MAXR=5
MAXSIZE=1024
MAXSPLIT=2
MAXT=1
MAX_AGE=0
MAX_ALLOWED=1
MAX_AVAILABLE_HEIGHT=10000
MAX_BACKWARDS=500
MAX_BYTES=4096
MAX_BYTES_WRITTEN=32767
MAX_CONNECTIONS=10
MAX_CONSTRAINT_NAME_LENGTH=64
MAX_COUNT=2048
MAX_DOC_LENGTH=72
MAX_EMAIL_LENGTH=2048
MAX_ERRORS=3
MAX_FRAMES=50
MAX_GROUP_DEPTH=10
MAX_GROUP_WIDTH=15
MAX_HEAP_PERCENT_OVERLOAD=15
MAX_HEIGHT=16
MAX_HELP_POSITION=28
MAX_HISTORY_DAYS=365
MAX_IDENTIFIER_LENGTH=63
MAX_IDLE_TIME=10
MAX_INDENT=0
MAX_INDEX_NAME_LENGTH=64
MAX_INTERVAL=1
MAX_ITEMS=2
MAX_ITER=600
MAX_ITERATIONS=1
MAX_KEEPALIVE_CONNECTIONS=20
MAX_LENGTH=20
MAX_LINE_LENGTH=79
MAX_LONG_STRINGS=16
MAX_MESSAGE_COUNT=1
MAX_NUMBER_OF_BITS_TO_USE=28
MAX_OPT=0
MAX_POOL_SIZE=10
MAX_PRIORITY=9
MAX_PROBER_CONFIDENCE=0.0
MAX_PURGE_COUNT=10
MAX_PYTHON_ARGS=255
MAX_RECORDS=100
MAX_REDIRECTS=6
MAX_REPEAT=1
MAX_RESTARTS=100
MAX_RETRIES=1
MAX_ROUNDS=4294967295
MAX_SALT_SIZE=4
MAX_SALT_VALUE=52
MAX_SHEBANG_LENGTH=512
MAX_SIZE=1000
MAX_STR_INT=4300
MAX_SYNC_CHUNK_SIZE=1024
MAX_TASKS_IN_MEMORY=1
MAX_TUPLE_ITEMS=10
MAX_UNION_ITEMS=10
MAX_URL_LENGTH=65536
MAX_VALUE=1.0
MAX_WAIT_TIME=0.2
MAX_WIDTH=80
MAX_WORKERS=1
MAX_WORKER_IDLE_TIME=30
MESSAGE_BUFFER_MAX=8192
MESSAGE_RETENTION_DURATION=600
MILLER_RABIN_TEST_COUNT=0
MIN=0
MINIMIZE_BOOLEAN_ATTRIBUTES=True
MINIMUM_LENGTH=0
MINOR=0
MINORVERSION=0
MINOR_VERSION=0
MINUTE=0
MINUTES=1
MINVAL=1
MIN_API_LEVEL=16
MIN_COLUMN_DISTANCE=3
MIN_FINAL_CHAR_DISTANCE=5
MIN_INDENT=1
MIN_INPUT_LEN=1
MIN_ITEMS=0
MIN_JSON_VERSION=1
MIN_LENGTH=1
MIN_LINES_BACKWARDS=50
MIN_MEMORY_COST=8
MIN_MODEL_DISTANCE=0.01
MIN_OFFSET=0
MIN_PAYLOAD_FOR_WRITELINES=2048
MIN_PRIORITY=0
MIN_REDRAW_INTERVAL=0.05
MIN_REPEAT=1
MIN_ROUNDS=0
MIN_SALT_SIZE=0
MIN_SALT_VALUE=0
MIN_SCROLL=0
MIN_TASK_WIDTH=16
MIN_VALUE=0.0
MIN_VERIFY_TIME=0
MIN_VOLUME_RATIO=1.2
MIN_WIDTH=7
MIN_WORKER_WIDTH=15
MOUSE_SUPPORT=True
MVT_ESTIMATE_MAX_SAMPLES=20
MVT_ESTIMATE_MAX_TIME=2
MVT_ESTIMATE_MIN_SAMPLES=10
MVT_ESTIMATE_RESOLUTION=0.01
NEEDS_EXPORT=True
NEWLINE_COUNT=0
NOMINAL=True
NOT_IMPORTS=True
NOT_SUPPORTED=1
NOWAIT=False
NO_DIALECT_SUPPORT=4
NUMBER=0
ONE_CHAR_PROB=0.5
ONLY_SHOW_AS_IMPORTS=True
OUTERLOOPCOUNTER=0
PAD_SIZE=32
PARENTHESIZED_CONTEXT_MANAGERS=17
PARSE_CHUNKED_SIZE=0
PCT=0.0
PERCENT=1.0
POLLING_INTERVAL=0.1
PORT=8000
POSITIONAL_COUNT=0
PREFETCH_COUNT=0
PREFETCH_COUNT_MAX=65535
PREPARE_MODELS_MAX_RETRIES=10
PRICE_CHANGE_PCT=2.5
PRICE_WEIGHT=0.4
PRIM_INTMAX=46
PRIM_SIZE=28
PRIM_SSIZE=29
PRIM_UINTMAX=47
P_TERMINATES=True
R=0.01
READ_COUNT=0
RECV_BUFSIZE=65536
REFRESH_INTERVAL=0.3
REMOVED_COUNT=0
REPORTED_RESULTS_COUNT=0
REQUESTS_PER_MINUTE=100
REQUIRES_TERMINATE_FOR_CLOSE=False
RESULTREPR_MAXSIZE=1024
RETRIES_BACKOFF_FACTOR=0.5
RETRY_ALL_ATTEMPT_BROKEN=False
RETRY_ATTEMPT=0
RETRY_ATTEMPTS=0
RETRY_FIRST_CONNECTION_ATTEMPT=True
RETRY_GUARANTEE_MESSAGE_CONSUMPTION_RETRY_INTERVAL=0.1
RETRY_IS_NO_ATTEMPT=True
RETRY_RETRY=True
RETRY_RETRY_ATTEMPTS=3
RETRY_RETRY_DISABLED=False
RETRY_RETRY_GEN=0
RETRY_RETRY_PERSISTENT_CONNECTION=False
RETRY_SHOULD_RETRY=False
RETRY__MAX_RECOVERY_ATTEMPTS=500
REUSE_GENERATOR_MAX_DISTANCE=100
REVEAL_IMPORTED=True
ROWCOUNT=0
SALT_SIZE=12
SAMPLE_SIZE=64
SAW_IMPORT=True
SENTINEL_COUNTER=0
SERVER_MAX_WINDOW_BITS=12
SETINPUTSIZES=2
SHA256_CRYPT__MIN_ROUNDS=535000
SHA512_CRYPT__MIN_ROUNDS=535000
SHAPE_COUNTER=14
SHOW_NUMBERS=True
SIGNAL_DURATION=24
SIGNED_INT_MAX=2147483647
SIZE=0
SIZE_ALERT=False
SKIPPED_COVERED_COUNT=0
SKIPPED_EMPTY_COUNT=0
SPREAD_WEIGHT=0.4
SQS_MAX_MESSAGES=10
SSL_BLOCKSIZE=16384
SSL_WRITE_BLOCKSIZE=16384
STRAIGHT_IMPORT=True
STR_MIN_LENGTH=0
SUBPOLLING_INTERVAL=0.5
SUPPORTCONSTRUCTEDFORM=True
SUPPORTED=True
SUPPORTINDEFLENGTH=True
SUPPORTINDEFLENMODE=True
SUPPORTS_ALTER=True
SUPPORTS_AUTOEXPIRE=True
SUPPORTS_CAST=True
SUPPORTS_COMMENTS=True
SUPPORTS_CONSTRAINT_COMMENTS=True
SUPPORTS_DEFAULT_METAVALUE=True
SUPPORTS_DEFAULT_VALUES=True
SUPPORTS_EMPTY_INSERT=True
SUPPORTS_EXEC=True
SUPPORTS_FANOUT=True
SUPPORTS_IDENTITY_COLUMNS=True
SUPPORTS_IS_DISTINCT_FROM=True
SUPPORTS_LONE_SURROGATES=True
SUPPORTS_MULTIVALUES_INSERT=True
SUPPORTS_NATIVE_BOOLEAN=True
SUPPORTS_NATIVE_DECIMAL=True
SUPPORTS_NATIVE_ENUM=True
SUPPORTS_NATIVE_JOIN=True
SUPPORTS_NATIVE_UUID=True
SUPPORTS_POPULATION=True
SUPPORTS_SANE_MULTI_ROWCOUNT=True
SUPPORTS_SANE_ROWCOUNT=True
SUPPORTS_SANE_ROWCOUNT_RETURNING=True
SUPPORTS_SCHEMAS=True
SUPPORTS_SEQUENCES=True
SUPPORTS_SERVER_SIDE_CURSORS=True
SUPPORTS_SIMPLE_ORDER_BY_LABEL=True
SUPPORTS_SINGLE_ENTITY=True
SUPPORTS_SMALLSERIAL=True
SUPPORTS_STATEMENT_CACHE=True
SUPPORTS_UNICODE_BINDS=True
SUPPORTS_UNICODE_STATEMENTS=True
SUPPORTS_UNIQUE_CONSTRAINTS=True
SUPPORTS_VIEWS=True
SURE_NO=0.01
SURE_YES=0.99
TABSIZE=8
TASKS_WAITING=0
TASK_COUNT=0
TECHNICAL_WEIGHT=0.3
TERMINAL=True
TERMINAL_SUPPORTS_COLOR=True
TERMINATE=True
TEXT_COUNT=0
THRESHOLD_DEFAULT_RECURSE_LIMIT=511
THRESHOLD_DEFAULT_REDIRECT_LIMIT=30
THRESHOLD_ENOUGH_DATA_THRESHOLD=1024
THRESHOLD_ENOUGH_REL_THRESHOLD=100
THRESHOLD_EXCEEDS_COST_THRESHOLD=True
THRESHOLD_GUARANTEE_MESSAGE_CONSUMPTION_RETRY_LIMIT=300
THRESHOLD_HIGH_WATER_LIMIT=65536
THRESHOLD_LIMIT=0
THRESHOLD_LIMIT_ON_ENTITY=False
THRESHOLD_LIST_BUILDING_EXPANSION_THRESHOLD=10
THRESHOLD_MAX_REL_THRESHOLD=1000
THRESHOLD_MINIMUM_DATA_THRESHOLD=3
THRESHOLD_MINIMUM_THRESHOLD=0.2
THRESHOLD_NEGATIVE_SHORTCUT_THRESHOLD=0.05
THRESHOLD_POSITIVE_SHORTCUT_THRESHOLD=0.95
THRESHOLD_RATE_LIMIT=1000
THRESHOLD_RESULTLIMIT=40
THRESHOLD_SB_ENOUGH_REL_THRESHOLD=1024
THRESHOLD_SHORTCUT_THRESHOLD=0.95
THRESHOLD_TAGS_LIMITED=True
THRESHOLD_TAG_LIMIT=10
THRESHOLD_UNLIMITED_RECURSION=False
THRESHOLD_VOLUME_SPIKE_THRESHOLD=2.0
THRESHOLD__LIMITED_DICT_SIZE=100
TIMEOUT_CAN_DELAY=True
TIMEOUT_CONNECTION_TIMEOUT=20.0
TIMEOUT_CONNECT_TIMEOUT=5
TIMEOUT_CPR_TIMEOUT=2
TIMEOUT_DEFAULT_RETRY_TIMEOUT_SECONDS=300
TIMEOUT_DEFAULT_TIMEOUT=0.2
TIMEOUT_DEFAULT_VISIBILITY_TIMEOUT=1800
TIMEOUT_DELAYED=False
TIMEOUT_ENABLE_TIMEOUTS=True
TIMEOUT_ES_RETRY_ON_TIMEOUT=False
TIMEOUT_ES_TIMEOUT=10
TIMEOUT_EXECUTION_DELAY_MS=100
TIMEOUT_HANDLE_TIMEOUTS=True
TIMEOUT_HTTP_408_REQUEST_TIMEOUT=408
TIMEOUT_HTTP_504_GATEWAY_TIMEOUT=504
TIMEOUT_IGNORE_TIMEOUTS=True
TIMEOUT_KEEPALIVE_TIMEOUT=15.0
TIMEOUT_LOST_WORKER_TIMEOUT=10.0
TIMEOUT_PROC_ALIVE_TIMEOUT=4.0
TIMEOUT_RAISE_ON_TIMEOUT=False
TIMEOUT_REQUEST_TIMEOUT=30.0
TIMEOUT_RETRY_DELAY=1.0
TIMEOUT_SCREEN_DELAY=10
TIMEOUT_SHUTDOWN_SOCKET_TIMEOUT=5.0
TIMEOUT_STATUS_CODE_GATEWAY_TIMEOUT=504
TIMEOUT_STATUS_CODE_NETWORK_CONNECT_TIMEOUT_ERROR=599
TIMEOUT_STATUS_CODE_REQUEST_TIMEOUT=408
TIMEOUT_TIMEOUT=0.5
TIMEOUT_TIMEOUT_MAX=10000000000.0
TIMEOUT_TIMEOUT_SECONDS=5
TIMEOUT_VISIBILITYTIMEOUT=0
TIMEOUT_VISIBILITY_TIMEOUT=3600
TIMEOUT_WAIT_TIMEOUT=258
TIMEOUT_YIELD_ON_TIMEOUT=True
TIMEOUT__SOCKET_TIMEOUT=15
TLS_RECORD_SIZE=16384
TOTAL_RUN_COUNT=0
TRUNCATE_SIZE=8
TYPE_VAR_TUPLE_ENCOUNTERED=False
TYPICAL_POSITIVE_RATIO=0.947368
UCOUNT=0
UINT32_SIZE=4
UNLIKE=0.99
UNSUPPORTED_DATA=1003
USE_PYSSIZE_T=True
VOLUME_CHANGE_PCT=15.0
VOLUME_WEIGHT=0.6
WAIT=True
WAIT_FOR_CLOSE=False
WAIT_FOR_NL=False
WAIT_TIME_SECONDS=0
WORKER_MAX_IDLE_TIME=300
WRAP_COUNT=0
WRITE_SUPPORT=True
WS_1003_UNSUPPORTED_DATA=1003
_ASSERT_NEVER_REPR_MAX_LENGTH=100
_BCRYPT_SUPPORTED=True
_BZ2_SUPPORTED=True
_CHUNKSIZE=500
_CONSUMING=False
_COUNT=0
_CX_ORACLE_MAGIC_LOB_SIZE=131072
_DEFAULTCHUNKSIZE=10240
_DEFAULT_ENCODE_SIZE=512
_DEFAULT_IDNA_SIZE=256
_FINAL_ITERATION=False
_FIPS_DH_MIN_KEY_SIZE=2048
_FIPS_RSA_MIN_KEY_SIZE=2048
_FIPS_RSA_MIN_PUBLIC_EXPONENT=65537
_HIERARCHY_SUPPORTS_CACHING=True
_IS_METADATA_OPERATION=True
_MAX_CANDIDATE_ITEMS=750
_MAX_CLOCK_SKEW=60
_MAX_DIGEST_SIZE=64
_MAX_STRING_SIZE=40
_MAX_STR_VALUE_SIZE=536870912
_MIN_ACK_DEADLINE=10
_MIN_DIGEST_SIZE=1
_MIN_KEY_SIZE=10
_MIN_SCHEDULED_COOKIE_EXPIRATION=100
_OPTIONALMINUTES=False
_PER_MIGRATION=True
_REQUIRE_AWAIT=False
_SOURCE_SUPPORTS_SCALARS=True
_SSHKEY_CERT_MAX_PRINCIPALS=256
_SUPPORTS_CREATE_INDEX_CONCURRENTLY=True
_SUPPORTS_DERIVED_COLUMNS=True
_SUPPORTS_DROP_INDEX_CONCURRENTLY=True
_SUPPORTS_DYNAMIC_ITERATION=True
_SUPPORTS_IMPLICIT_RETURNING=True
_SUPPORTS_MULTI_PARAMETERS=True
_SUPPORTS_NVARCHAR_MAX=False
_SUPPORTS_OFFSET_FETCH=True
_SUPPORT_ASYNC=True