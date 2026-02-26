# 石井屋員林 空調監控系統

## 專案概述
透過 Modbus TCP 連線永宏 PLC (59.125.52.73:502)，實現空調設備監控與手動控制的 Web App。
**重要設計原則**: Web App 僅作為監控/手動控制介面，所有自動控制邏輯由 PLC 內部程式處理。
**品牌**: 金毅泰節能 (header logo: static/logo.png)

## 技術堆疊
- **後端**: Python 3.11 + Flask + Waitress WSGI
- **通訊**: pymodbus (Modbus TCP) + ModbusManager 連線管理
- **AI/ML**: PyTorch (AutoEncoder 異常偵測) + numpy (統計方法備援)
- **前端**: HTML/CSS/JavaScript (Traditional Chinese UI, 工業風深色主題)
- **部署**: gunicorn (autoscale), bash 自動重啟包裝器
- **穩定性**: run.sh 包裝器自動重啟 Python 程序

## 專案結構
```
app.py              # Flask 主應用 + API 路由
config.py           # 系統設定（IO 對照表、電表暫存器、Slave ID、FATEK 位址轉換）
modbus_manager.py   # Modbus 連線管理器（單例模式、自動重連、重試、執行緒安全）
ml_engine.py        # ML 引擎（資料收集、PyTorch AutoEncoder、統計異常偵測）
run.sh              # 自動重啟包裝器（解決 Replit 工作流程穩定性問題）
gunicorn_config.py  # Gunicorn 部署設定
templates/
  index.html        # 前端頁面
static/
  style.css         # 樣式（深色工業主題、動畫風扇圖示）
  app.js            # 前端邏輯（5分頁、即時輪詢）
  logo.png          # 金毅泰節能公司 LOGO
ml_data/            # ML 資料儲存目錄
```

## 永宏 PLC Modbus 位址對照 (Base-0)
| PLC 暫存器 | Modbus 5位數 | Base-0 Offset | 說明 |
|-----------|-------------|---------------|------|
| Y0~Y255   | -           | 0~255         | 數位輸出 (線圈, FC01/05) |
| R0~R4167  | 40001~44168 | 0~4167        | 保持暫存器 (FC03) |
| R5000~R5998 | 45001~45999 | 5000~5998   | 唯讀暫存器 (ROR) |
| D0~D2998  | 46001~48999 | 6000~8998     | 資料暫存器 (FC03) |

## 資料存放位址

### 電表資料 (FC03 讀 R 暫存器, IEEE 754 浮點)
- **電表1**: R4~R67 (R0~R3 被 PLC 覆寫, 非電壓值)
- **電表2**: R100~R167 (完整三相)
- 簡化顯示: 電壓/電流/kW/PF

### 溫度資料 (FC03 讀 R 暫存器, 整數 /10 °C)
- **位址**: R1000~R1011 (12 通道)
- 活躍通道: CH0~CH3, CH8~CH11
- CH4~CH7: 未接線

## A箱空調 DO 對照 (Slave 3, Y0~Y63, 64 coils)

### 冰水機 (2 台)
| Y 位址 | 設備名稱 | 控制方式 |
|--------|---------|---------|
| Y0 | 冰水機1 | 開/關 |
| Y1 | 冰水機2 | 開/關 |

### 雙速送風機 (14 台, Y_L=啟動+弱風, Y_H=強風)
| Y_L / Y_H | 設備名稱 |
|-----------|---------|
| Y2/Y3 | 新娘休息室送風機 |
| Y38/Y39 | 壽司吧左前送風機 |
| Y40/Y41 | 壽司吧右前送風機 |
| Y42/Y43 | 壽司吧左側送風機 |
| Y44/Y45 | 壽司吧右側送風機 |
| Y46/Y47 | 小吃區右左送風機 |
| Y48/Y49 | 石洗碗區送風機 |
| Y50/Y51 | 廁所送風機 |
| Y52/Y53 | 大廳送風機 |
| Y54/Y55 | 包廂櫃台走道送風機 |
| Y56/Y57 | 廁所前走道送風機 |
| Y58/Y59 | 舞洗碗區送風機 |
| Y60/Y61 | 廚房後送風機 |
| Y62/Y63 | 廚房前送風機 |

### 單速送風機 (13 台, 開/關)
| Y 位址 | 設備名稱 |
|--------|---------|
| Y4 | 大美送風機 |
| Y6 | 清風送風機 |
| Y8 | 水月1送風機 |
| Y10 | 水月2送風機 |
| Y12 | 舞雪送風機 |
| Y14 | 如雲送風機 |
| Y16 | 初日送風機 |
| Y18 | 澄淨送風機 |
| Y20 | 歸真送風機 |
| Y22 | 小雅送風機 |
| Y32 | 千江1送風機 |
| Y34 | 千江2送風機 |
| Y36 | 千江3送風機 |

## B箱空調 DO 對照 (Slave 4, Y0~Y28, 29 coils)

### 雙速送風機 (14 台)
| Y_L / Y_H | 設備名稱 |
|-----------|---------|
| Y0/Y1 | 廚房送風機 |
| Y2/Y3 | 工作區送風機 |
| Y4/Y5 | 咖啡吧送風機 |
| Y6/Y7 | 排排坐1.2送風機 |
| Y8/Y9 | 廁所前1.2送風機 |
| Y10/Y11 | 高腳椅送風機 |
| Y12/Y13 | 1區後送風機 |
| Y14/Y15 | 1區前送風機 |
| Y16/Y17 | 大廳送風機 |
| Y18/Y19 | 半圓沙發前送風機 |
| Y20/Y21 | 半圓沙發後送風機 |
| Y22/Y23 | 玻璃屋中送風機 |
| Y24/Y25 | 玻璃屋後送風機 |
| Y26/Y27 | 玻璃屋前送風機 |

### 其他控制
| Y 位址 | 設備名稱 |
|--------|---------|
| Y28 | 燈光總盤 |

## 功能模組

### 電表監控 (220V/380V 三相四線, CT 400:5A)
- 電表1 (Slave 1): R4~R67, 電表2 (Slave 2): R100~R167
- 簡化顯示: 電壓、電流、功率(kW)、功率因數

### A箱空調手動控制 (Slave 3, Y0~Y63)
- 冰水機 1, 2 (Y0, Y1) - 開/關
- 14 台雙速送風機 - 關/弱/強 (Y_L=啟動+弱風, Y_H=強風)
- 13 台單速送風機 - 開/關

### B箱空調手動控制 (Slave 4, Y0~Y28)
- 14 台雙速送風機 + Y28 燈光總盤
- UI 顯示個別 Y_L/Y_H DO 狀態指示器 + 動畫風扇圖示

### PLC 總覽
- 監控專用分頁，顯示 PLC 即時狀態
- 溫度、A/B 箱線圈狀態一覽

### AI 異常偵測
- Z-score 統計方法 + PyTorch AutoEncoder
- 即時溫度異常偵測

## API 端點
- `GET /api/status` - PLC 連線狀態
- `GET /api/config` - 系統設定 (含 box_a.dual_fans, box_a.single_fans, box_b.fans)
- `GET /api/meter/<slave_id>` - 電表讀取
- `GET /api/hvac/<box>/status` - HVAC 線圈狀態
- `POST /api/hvac/<box>/coil` - 寫入線圈
- `POST /api/hvac/<box>/fan` - 送風機速度控制 (支援雙速 y_l+y_h 和單速 y_l only)
- `GET /api/temperatures` - PT100 溫度
- `GET /api/plc/overview` - PLC 總覽
- `GET /api/ml/status` - ML 系統狀態
- `POST /api/ml/train` - 訓練 AutoEncoder
- `GET /api/ml/analyze` - 異常分析

## 環境變數
- `PLC_HOST` - PLC IP (預設: 59.125.52.73)
- `PLC_PORT` - Modbus 埠 (預設: 502)
- `METER1_SLAVE_ID` / `METER2_SLAVE_ID` - 電表 Slave ID (預設: 1, 2)
- `PLC_A_SLAVE_ID` / `PLC_B_SLAVE_ID` - PLC Slave ID (預設: 3, 4)
- `SESSION_SECRET` - Flask session 密鑰

## 已知事項
- Replit 工作流程會在 ~20 秒後終止 Python 程序，使用 run.sh 包裝器自動重啟
- Modbus 操作序列化存取 (single lock)
- 直接 `python app.py` 程序完全穩定，問題僅出在工作流程管理器
