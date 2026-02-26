import os
import json
import time
import threading
import logging
import numpy as np
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "ml_data")
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
MODEL_FILE = os.path.join(DATA_DIR, "anomaly_model.pt")


class DataCollector:
    def __init__(self, max_points=5000):
        self._lock = threading.Lock()
        self.max_points = max_points
        self.temperature_history = deque(maxlen=max_points)
        self.hvac_history = deque(maxlen=max_points)
        self._load_history()

    def _load_history(self):
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                for item in data.get("temperature", []):
                    self.temperature_history.append(item)
                for item in data.get("hvac", []):
                    self.hvac_history.append(item)
                logger.info(f"載入歷史資料: 溫度 {len(self.temperature_history)} 筆, HVAC {len(self.hvac_history)} 筆")
        except Exception as e:
            logger.warning(f"載入歷史資料失敗: {e}")

    def save_history(self):
        try:
            with self._lock:
                data = {
                    "temperature": list(self.temperature_history),
                    "hvac": list(self.hvac_history),
                }
            with open(HISTORY_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"儲存歷史資料失敗: {e}")

    def record_temperature(self, channels):
        with self._lock:
            entry = {
                "timestamp": time.time(),
                "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channels": channels,
            }
            self.temperature_history.append(entry)

    def record_hvac(self, box, coils):
        with self._lock:
            on_count = sum(1 for v in coils.values() if v)
            entry = {
                "timestamp": time.time(),
                "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "box": box,
                "on_count": on_count,
                "total": len(coils),
            }
            self.hvac_history.append(entry)

    def get_temperature_series(self, channel="CH0", limit=200):
        with self._lock:
            series = []
            for entry in self.temperature_history:
                ch_data = entry.get("channels", {}).get(channel, {})
                temp = ch_data.get("temperature")
                if temp is not None:
                    series.append({
                        "timestamp": entry["timestamp"],
                        "time_str": entry["time_str"],
                        "value": temp,
                    })
            return series[-limit:]

    def get_hvac_series(self, box="a", limit=200):
        with self._lock:
            series = []
            for entry in self.hvac_history:
                if entry.get("box") == box:
                    series.append({
                        "timestamp": entry["timestamp"],
                        "time_str": entry["time_str"],
                        "on_count": entry["on_count"],
                        "total": entry["total"],
                    })
            return series[-limit:]


class AnomalyDetector:
    def __init__(self, window_size=30, z_threshold=2.5):
        self._lock = threading.Lock()
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.channel_windows = {}
        self.torch_model = None
        self._torch_available = False
        self._torch_initialized = False

    def _ensure_torch(self):
        if self._torch_initialized:
            return
        self._torch_initialized = True
        try:
            import torch
            import torch.nn as nn

            class AutoEncoder(nn.Module):
                def __init__(self, input_dim=10):
                    super().__init__()
                    self.encoder = nn.Sequential(
                        nn.Linear(input_dim, 8),
                        nn.ReLU(),
                        nn.Linear(8, 4),
                        nn.ReLU(),
                        nn.Linear(4, 2),
                    )
                    self.decoder = nn.Sequential(
                        nn.Linear(2, 4),
                        nn.ReLU(),
                        nn.Linear(4, 8),
                        nn.ReLU(),
                        nn.Linear(8, input_dim),
                    )

                def forward(self, x):
                    encoded = self.encoder(x)
                    decoded = self.decoder(encoded)
                    return decoded

            self.torch_model = AutoEncoder(input_dim=10)
            self.torch_model.eval()

            if os.path.exists(MODEL_FILE):
                self.torch_model.load_state_dict(torch.load(MODEL_FILE, weights_only=True))
                logger.info("載入已訓練的異常偵測模型")
            else:
                logger.info("PyTorch 異常偵測模型初始化完成 (未訓練)")

            self._torch_available = True
        except Exception as e:
            logger.warning(f"PyTorch 初始化失敗，使用統計方法: {e}")
            self._torch_available = False

    def update(self, channel, value):
        with self._lock:
            if channel not in self.channel_windows:
                self.channel_windows[channel] = deque(maxlen=self.window_size)
            self.channel_windows[channel].append(value)

    def check_statistical(self, channel, value):
        with self._lock:
            window = self.channel_windows.get(channel)
            if not window or len(window) < 5:
                return {"anomaly": False, "reason": None, "confidence": 0}

            values = list(window)
            mean = np.mean(values)
            std = np.std(values)

            if std < 0.1:
                if abs(value - mean) > 1:
                    return {
                        "anomaly": True,
                        "reason": f"數值突變 ({mean:.1f} → {value})",
                        "confidence": 0.8,
                        "mean": round(float(mean), 1),
                        "std": round(float(std), 2),
                    }
                return {"anomaly": False, "reason": None, "confidence": 0}

            z_score = abs(value - mean) / std

            if z_score > self.z_threshold:
                return {
                    "anomaly": True,
                    "reason": f"Z-score {z_score:.1f} 超過閾值 {self.z_threshold}",
                    "confidence": min(float(z_score / (self.z_threshold * 2)), 1.0),
                    "z_score": round(float(z_score), 2),
                    "mean": round(float(mean), 1),
                    "std": round(float(std), 2),
                }

            return {
                "anomaly": False,
                "reason": None,
                "confidence": 0,
                "z_score": round(float(z_score), 2),
            }

    def check_torch(self, channel):
        self._ensure_torch()
        if not self._torch_available:
            return None

        with self._lock:
            window = self.channel_windows.get(channel)
            if not window or len(window) < 10:
                return None

        try:
            import torch

            values = list(window)[-10:]
            arr = np.array(values, dtype=np.float32)

            if np.std(arr) > 0.01:
                arr = (arr - np.mean(arr)) / np.std(arr)
            else:
                arr = arr - np.mean(arr)

            tensor = torch.FloatTensor(arr).unsqueeze(0)

            with torch.no_grad():
                reconstructed = self.torch_model(tensor)
                loss = torch.nn.functional.mse_loss(reconstructed, tensor).item()

            return {
                "reconstruction_error": round(loss, 4),
                "anomaly": loss > 0.5,
                "confidence": min(loss / 1.0, 1.0) if loss > 0.5 else 0,
            }
        except Exception as e:
            logger.debug(f"PyTorch 推論錯誤: {e}")
            return None

    def train_model(self, data_collector, channel="CH0", epochs=50):
        self._ensure_torch()
        if not self._torch_available:
            return {"success": False, "reason": "PyTorch 不可用"}

        series = data_collector.get_temperature_series(channel, limit=1000)
        if len(series) < 20:
            return {"success": False, "reason": f"資料不足 (需要 20 筆以上，目前 {len(series)} 筆)"}

        try:
            import torch
            import torch.nn as nn
            from torch.optim import Adam

            values = [s["value"] for s in series]
            sequences = []
            for i in range(len(values) - 10 + 1):
                seq = values[i:i + 10]
                sequences.append(seq)

            arr = np.array(sequences, dtype=np.float32)
            mean_val = np.mean(arr)
            std_val = np.std(arr)
            if std_val > 0.01:
                arr = (arr - mean_val) / std_val

            dataset = torch.FloatTensor(arr)

            optimizer = Adam(self.torch_model.parameters(), lr=0.001)
            criterion = nn.MSELoss()

            self.torch_model.train()
            losses = []
            for epoch in range(epochs):
                optimizer.zero_grad()
                output = self.torch_model(dataset)
                loss = criterion(output, dataset)
                loss.backward()
                optimizer.step()
                losses.append(loss.item())

            self.torch_model.eval()

            torch.save(self.torch_model.state_dict(), MODEL_FILE)

            return {
                "success": True,
                "samples": len(sequences),
                "final_loss": round(losses[-1], 6),
                "epochs": epochs,
            }
        except Exception as e:
            logger.error(f"模型訓練失敗: {e}")
            return {"success": False, "reason": str(e)}

    def analyze(self, channel, value):
        self.update(channel, value)

        result = {
            "channel": channel,
            "value": value,
            "statistical": self.check_statistical(channel, value),
        }

        torch_result = self.check_torch(channel)
        if torch_result:
            result["autoencoder"] = torch_result

        result["is_anomaly"] = (
            result["statistical"]["anomaly"]
            or (torch_result is not None and torch_result.get("anomaly", False))
        )

        return result


collector = DataCollector()
detector = AnomalyDetector()


def save_periodic():
    while True:
        time.sleep(60)
        collector.save_history()


_save_thread = threading.Thread(target=save_periodic, daemon=True)
_save_thread.start()
