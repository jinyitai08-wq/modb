import threading
import time
import logging
from pymodbus.client import ModbusTcpClient
from pymodbus.pdu import ExceptionResponse
from config import PLC_HOST, PLC_PORT

logger = logging.getLogger(__name__)

MODBUS_EXCEPTION_CODES = {
    1: "不合法的功能碼",
    2: "不合法的資料位址 - 該位址不存在",
    3: "不合法的資料值",
    4: "從站設備故障",
    5: "確認 - 處理中請稍後",
    6: "從站設備忙碌",
}


def parse_modbus_error(result):
    if isinstance(result, ExceptionResponse):
        fc = result.function_code - 0x80 if result.function_code >= 0x80 else result.function_code
        msg = MODBUS_EXCEPTION_CODES.get(result.exception_code, f"未知錯誤碼 {result.exception_code}")
        return f"Modbus 錯誤 (FC{fc}): {msg}"
    return f"Modbus 錯誤: {result}"


class ModbusManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client = None
        self._client_lock = threading.Lock()
        self._connect_time = 0
        self._fail_count = 0
        self._max_retries = 3
        self._base_timeout = 3
        self._max_backoff = 10
        self._stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "reconnects": 0,
            "last_error": None,
            "last_success": None,
        }
        logger.info(f"ModbusManager 初始化: {PLC_HOST}:{PLC_PORT}")

    def _get_client(self):
        if self._client is None or not self._client.connected:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = ModbusTcpClient(
                host=PLC_HOST,
                port=PLC_PORT,
                timeout=self._base_timeout,
                retries=1,
            )
            if self._client.connect():
                self._connect_time = time.time()
                was_failed = self._fail_count > 0
                self._fail_count = 0
                self._stats["reconnects"] += 1
                if was_failed or self._stats["reconnects"] <= 1:
                    logger.info("Modbus 連線成功")
                else:
                    logger.debug("Modbus 重新連線成功")
            else:
                self._client = None
                self._fail_count += 1
                raise ConnectionError("無法連線至 PLC")
        return self._client

    def _backoff_delay(self):
        if self._fail_count <= 0:
            return 0
        delay = min(0.5 * (2 ** (self._fail_count - 1)), self._max_backoff)
        return delay

    def execute(self, operation, *args, **kwargs):
        with self._client_lock:
            self._stats["total_requests"] += 1
            last_error = None

            for attempt in range(self._max_retries):
                if attempt > 0:
                    delay = self._backoff_delay()
                    if delay > 0:
                        time.sleep(delay)

                try:
                    client = self._get_client()
                    result = operation(client, *args, **kwargs)

                    if hasattr(result, 'isError') and result.isError():
                        error_msg = parse_modbus_error(result)
                        self._stats["failed"] += 1
                        self._stats["last_error"] = error_msg
                        return result

                    self._stats["successful"] += 1
                    self._stats["last_success"] = time.time()
                    self._fail_count = 0
                    return result

                except ConnectionError:
                    last_error = "無法連線至 PLC"
                    self._client = None
                    self._fail_count += 1
                    if attempt == 0:
                        logger.debug(f"連線失敗 (嘗試 {attempt + 1}/{self._max_retries})")
                    else:
                        logger.warning(f"連線失敗 (嘗試 {attempt + 1}/{self._max_retries})")

                except Exception as e:
                    last_error = str(e)
                    self._client = None
                    self._fail_count += 1
                    logger.warning(f"Modbus 錯誤 (嘗試 {attempt + 1}/{self._max_retries}): {e}")

            self._stats["failed"] += 1
            self._stats["last_error"] = last_error
            raise ConnectionError(f"重試 {self._max_retries} 次後仍失敗: {last_error}")

    def read_coils(self, address, count, device_id):
        def op(client, addr, cnt, dev):
            return client.read_coils(address=addr, count=cnt, device_id=dev)
        return self.execute(op, address, count, device_id)

    def write_coil(self, address, value, device_id):
        def op(client, addr, val, dev):
            return client.write_coil(address=addr, value=val, device_id=dev)
        return self.execute(op, address, value, device_id)

    def read_holding_registers(self, address, count, device_id):
        def op(client, addr, cnt, dev):
            return client.read_holding_registers(address=addr, count=cnt, device_id=dev)
        return self.execute(op, address, count, device_id)

    def read_input_registers(self, address, count, device_id):
        def op(client, addr, cnt, dev):
            return client.read_input_registers(address=addr, count=cnt, device_id=dev)
        return self.execute(op, address, count, device_id)

    def check_connection(self):
        try:
            with self._client_lock:
                client = self._get_client()
                return client.connected
        except Exception:
            return False

    def get_stats(self):
        return {
            **self._stats,
            "connected": self._client is not None and self._client.connected,
            "fail_count": self._fail_count,
            "uptime": time.time() - self._connect_time if self._connect_time > 0 else 0,
        }

    def close(self):
        with self._client_lock:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None


modbus = ModbusManager()
