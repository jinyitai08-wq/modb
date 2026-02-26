import os
import sys
import signal
import struct
import math
import time
import logging
from flask import Flask, render_template, jsonify, request
from modbus_manager import modbus, parse_modbus_error
from ml_engine import collector, detector
from config import (
    PLC_HOST, PLC_PORT,
    METER1_SLAVE_ID, METER2_SLAVE_ID,
    PLC_A_SLAVE_ID, PLC_B_SLAVE_ID, PLC_TEMP_SLAVE_ID,
    METER1_BASE_R, METER2_BASE_R,
    TEMP_COUNT, TEMP_R_REG,
    METER_CT_RATIO, METER1_PARAMS, METER2_PARAMS, METER_READ_COUNT,
    BOX_A_CHILLERS, BOX_A_DUAL_FANS, BOX_A_SINGLE_FANS, BOX_A_COIL_COUNT,
    BOX_B_FANS, BOX_B_SINGLES, BOX_B_COIL_COUNT,
    fatek_r_addr,
)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
logging.getLogger("waitress").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return jsonify({"error": "內部伺服器錯誤", "detail": str(error)}), 500


@app.errorhandler(Exception)
def unhandled_exception(error):
    logger.error(f"Unhandled Exception: {error}", exc_info=True)
    return jsonify({"error": "未預期的錯誤", "detail": str(error)}), 500


RTD_ERROR_CODES = {
    0x7FFF: "感測器斷線",
    0x8000: "感測器短路",
    0x7FFE: "超出量測上限",
    0x8001: "超出量測下限",
}


def regs_to_float(regs, offset):
    try:
        raw = struct.pack('>HH', regs[offset], regs[offset + 1])
        value = struct.unpack('>f', raw)[0]
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 2)
    except (IndexError, struct.error):
        return None


def convert_pt100_raw(raw_uint16):
    if raw_uint16 in RTD_ERROR_CODES:
        return {"raw": raw_uint16, "temperature": None, "error": RTD_ERROR_CODES[raw_uint16]}
    signed_val = raw_uint16 - 0x10000 if raw_uint16 >= 0x8000 else raw_uint16
    temperature = signed_val / 10.0
    return {"raw": raw_uint16, "temperature": round(temperature, 1), "error": None}


def read_all_temperatures():
    try:
        address = fatek_r_addr(TEMP_R_REG)
        result = modbus.read_holding_registers(address, TEMP_COUNT, PLC_TEMP_SLAVE_ID)
        if hasattr(result, 'isError') and result.isError():
            return None
        channels = {}
        for i, raw in enumerate(result.registers):
            ch_data = convert_pt100_raw(raw)
            ch_data["r_addr"] = TEMP_R_REG + i
            channels[f"CH{i}"] = ch_data
        return channels
    except Exception:
        return None


@app.route("/health")
def health():
    return "OK", 200


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"首頁渲染錯誤: {e}")
        return f"系統啟動中... ({e})", 200


@app.route("/api/status")
def api_status():
    connected = modbus.check_connection()
    stats = modbus.get_stats()
    return jsonify({
        "connected": connected,
        "host": PLC_HOST,
        "port": PLC_PORT,
        "stats": stats,
    })


@app.route("/api/config")
def api_config():
    return jsonify({
        "plc_host": PLC_HOST,
        "plc_port": PLC_PORT,
        "ct_ratio": METER_CT_RATIO,
        "meter1_slave": METER1_SLAVE_ID,
        "meter2_slave": METER2_SLAVE_ID,
        "plc_a_slave": PLC_A_SLAVE_ID,
        "plc_b_slave": PLC_B_SLAVE_ID,
        "temp_r_reg": TEMP_R_REG,
        "temp_count": TEMP_COUNT,
        "box_a": {
            "chillers": BOX_A_CHILLERS,
            "dual_fans": BOX_A_DUAL_FANS,
            "single_fans": BOX_A_SINGLE_FANS,
        },
        "box_b": {"fans": BOX_B_FANS, "singles": BOX_B_SINGLES},
    })


@app.route("/api/meter/<int:slave_id>")
def read_meter(slave_id):
    if slave_id == METER1_SLAVE_ID:
        base_r = METER1_BASE_R
        meter_params = METER1_PARAMS
        note = "R0~R3 被 PLC 覆寫，L1-N/L2-N 電壓不可用"
    elif slave_id == METER2_SLAVE_ID:
        base_r = METER2_BASE_R
        meter_params = METER2_PARAMS
        note = None
    else:
        return jsonify({"error": "無效的電表 Slave ID"}), 400

    try:
        modbus_addr = fatek_r_addr(base_r)
        result = modbus.read_holding_registers(modbus_addr, METER_READ_COUNT, PLC_A_SLAVE_ID)
        if hasattr(result, 'isError') and result.isError():
            err_msg = parse_modbus_error(result)
            logger.warning(f"電表 {slave_id} (R{base_r}) 讀取失敗: {err_msg}")
            return jsonify({"error": err_msg}), 500

        regs = result.registers

        params = []
        for p in meter_params:
            offset = p["offset"]
            value = regs_to_float(regs, offset)
            if value is not None and "div" in p:
                value = round(value / p["div"], 2)
            params.append({
                "name": p["name"],
                "value": value,
                "unit": p["unit"],
                "group": p["group"],
                "r_addr": base_r + offset,
            })

        resp = {
            "status": "success",
            "slave_id": slave_id,
            "base_r": base_r,
            "ct_ratio": METER_CT_RATIO,
            "params": params,
        }
        if note:
            resp["note"] = note
        return jsonify(resp)
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"讀取錯誤: {str(e)}"}), 500


@app.route("/api/hvac/<box>/status")
def hvac_status(box):
    if box == "a":
        slave_id = PLC_A_SLAVE_ID
        coil_count = BOX_A_COIL_COUNT
    elif box == "b":
        slave_id = PLC_B_SLAVE_ID
        coil_count = BOX_B_COIL_COUNT
    else:
        return jsonify({"error": "無效的箱號"}), 400

    try:
        result = modbus.read_coils(0, coil_count, slave_id)
        if hasattr(result, 'isError') and result.isError():
            return jsonify({"error": parse_modbus_error(result)}), 500

        coils = {}
        for i in range(coil_count):
            coils[str(i)] = result.bits[i]

        collector.record_hvac(box, coils)

        return jsonify({"status": "success", "box": box, "coils": coils})
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"讀取錯誤: {str(e)}"}), 500


@app.route("/api/hvac/<box>/coil", methods=["POST"])
def hvac_write_coil(box):
    if box == "a":
        slave_id = PLC_A_SLAVE_ID
    elif box == "b":
        slave_id = PLC_B_SLAVE_ID
    else:
        return jsonify({"error": "無效的箱號"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "請提供 JSON 資料"}), 400

    address = data.get("address")
    value = data.get("value")
    if address is None or value is None:
        return jsonify({"error": "需要 address 和 value"}), 400

    try:
        result = modbus.write_coil(int(address), bool(value), slave_id)
        if hasattr(result, 'isError') and result.isError():
            return jsonify({"error": parse_modbus_error(result)}), 500

        return jsonify({"success": True, "address": address, "value": bool(value)})
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"寫入錯誤: {str(e)}"}), 500


@app.route("/api/hvac/<box>/fan", methods=["POST"])
def hvac_fan_speed(box):
    if box == "a":
        slave_id = PLC_A_SLAVE_ID
    elif box == "b":
        slave_id = PLC_B_SLAVE_ID
    else:
        return jsonify({"error": "無效的箱號"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "請提供 JSON 資料"}), 400

    y_l = data.get("y_l")
    y_h = data.get("y_h")
    speed = data.get("speed")

    if y_h is None and y_l is not None and speed in ("off", "on"):
        try:
            val = speed == "on"
            r = modbus.write_coil(int(y_l), val, slave_id)
            if hasattr(r, 'isError') and r.isError():
                return jsonify({"error": parse_modbus_error(r)}), 500
            return jsonify({"success": True, "speed": speed})
        except ConnectionError as e:
            return jsonify({"error": str(e)}), 503
        except Exception as e:
            return jsonify({"error": f"寫入錯誤: {str(e)}"}), 500

    if y_l is None or y_h is None or speed not in ("off", "low", "high"):
        return jsonify({"error": "需要 y_l, y_h 和 speed (off/low/high)"}), 400

    if speed == "off":
        l_val, h_val = False, False
    elif speed == "low":
        l_val, h_val = True, False
    else:
        l_val, h_val = True, True

    try:
        r1 = modbus.write_coil(int(y_h), False, slave_id)
        if hasattr(r1, 'isError') and r1.isError():
            return jsonify({"error": parse_modbus_error(r1)}), 500

        r2 = modbus.write_coil(int(y_l), l_val, slave_id)
        if hasattr(r2, 'isError') and r2.isError():
            return jsonify({"error": parse_modbus_error(r2)}), 500

        if h_val:
            r3 = modbus.write_coil(int(y_h), True, slave_id)
            if hasattr(r3, 'isError') and r3.isError():
                return jsonify({"error": parse_modbus_error(r3)}), 500

        return jsonify({"success": True, "speed": speed})
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"寫入錯誤: {str(e)}"}), 500


@app.route("/api/temperatures")
def get_temperatures():
    r_reg = request.args.get("r_reg", TEMP_R_REG, type=int)
    count = request.args.get("count", TEMP_COUNT, type=int)

    if count < 1 or count > 32:
        return jsonify({"error": "數量必須在 1~32 之間"}), 400

    address = fatek_r_addr(r_reg)

    try:
        result = modbus.read_holding_registers(address, count, PLC_TEMP_SLAVE_ID)
        if hasattr(result, 'isError') and result.isError():
            return jsonify({"error": parse_modbus_error(result)}), 500

        channels = {}
        for i, raw in enumerate(result.registers):
            ch_name = f"CH{i}"
            ch_data = convert_pt100_raw(raw)
            ch_data["r_addr"] = r_reg + i
            channels[ch_name] = ch_data

            if ch_data["temperature"] is not None and ch_data["temperature"] != 0:
                analysis = detector.analyze(ch_name, ch_data["temperature"])
                ch_data["anomaly"] = analysis.get("is_anomaly", False)
                if analysis.get("is_anomaly"):
                    ch_data["anomaly_info"] = {
                        "statistical": analysis.get("statistical", {}),
                        "autoencoder": analysis.get("autoencoder"),
                    }
            else:
                ch_data["anomaly"] = False

        collector.record_temperature(channels)

        return jsonify({
            "status": "success",
            "r_reg": r_reg,
            "address": address,
            "data": channels,
        })
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"讀取錯誤: {str(e)}"}), 500


@app.route("/api/plc/overview")
def plc_overview():
    result = {"status": "success"}
    try:
        temps = read_all_temperatures()
        if temps:
            result["temperatures"] = temps
        else:
            result["temperatures"] = None
            result["temp_error"] = "溫度讀取失敗"
    except Exception as e:
        result["temperatures"] = None
        result["temp_error"] = str(e)

    try:
        b_coils_result = modbus.read_coils(0, BOX_B_COIL_COUNT, PLC_B_SLAVE_ID)
        if hasattr(b_coils_result, 'isError') and b_coils_result.isError():
            result["box_b_coils"] = None
            result["box_b_error"] = "B箱線圈讀取錯誤"
            logger.warning("PLC 總覽: B箱線圈讀取失敗")
        else:
            coils = {}
            for i in range(BOX_B_COIL_COUNT):
                coils[str(i)] = b_coils_result.bits[i]
            result["box_b_coils"] = coils
    except Exception as e:
        result["box_b_coils"] = None
        result["box_b_error"] = str(e)
        logger.warning(f"PLC 總覽: B箱線圈例外 - {e}")

    try:
        a_coils_result = modbus.read_coils(0, BOX_A_COIL_COUNT, PLC_A_SLAVE_ID)
        if hasattr(a_coils_result, 'isError') and a_coils_result.isError():
            result["box_a_coils"] = None
            result["box_a_error"] = "A箱線圈讀取錯誤"
            logger.warning("PLC 總覽: A箱線圈讀取失敗")
        else:
            coils = {}
            for i in range(BOX_A_COIL_COUNT):
                coils[str(i)] = a_coils_result.bits[i]
            result["box_a_coils"] = coils
    except Exception as e:
        result["box_a_coils"] = None
        result["box_a_error"] = str(e)
        logger.warning(f"PLC 總覽: A箱線圈例外 - {e}")

    return jsonify(result)


@app.route("/api/ml/status")
def ml_status():
    stats = modbus.get_stats()
    return jsonify({
        "modbus": stats,
        "ml": {
            "temperature_records": len(collector.temperature_history),
            "hvac_records": len(collector.hvac_history),
            "torch_available": detector._torch_available,
            "channels_tracked": list(detector.channel_windows.keys()),
        },
    })


@app.route("/api/ml/history/temperature")
def ml_temp_history():
    channel = request.args.get("channel", "CH0")
    limit = request.args.get("limit", 200, type=int)
    series = collector.get_temperature_series(channel, limit)
    return jsonify({"channel": channel, "count": len(series), "data": series})


@app.route("/api/ml/history/hvac")
def ml_hvac_history():
    box = request.args.get("box", "a")
    limit = request.args.get("limit", 200, type=int)
    series = collector.get_hvac_series(box, limit)
    return jsonify({"box": box, "count": len(series), "data": series})


@app.route("/api/ml/train", methods=["POST"])
def ml_train():
    channel = request.args.get("channel", "CH0")
    epochs = request.args.get("epochs", 50, type=int)
    result = detector.train_model(collector, channel, epochs)
    return jsonify(result)


@app.route("/api/ml/analyze")
def ml_analyze():
    results = {}
    for channel, window in detector.channel_windows.items():
        if len(window) > 0:
            latest_value = window[-1]
            results[channel] = detector.analyze(channel, latest_value)
    return jsonify({"channels": results})


if __name__ == "__main__":
    import socket

    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.warning(f"收到信號 {sig_name} ({signum})")
        if signum in (signal.SIGTERM, signal.SIGINT):
            modbus.close()
            sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    try:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGWINCH, signal.SIG_IGN)
    except (OSError, AttributeError):
        pass

    port = int(os.environ.get("PORT", "5000"))

    def wait_for_port(p, timeout=15):
        start = time.time()
        while time.time() - start < timeout:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            try:
                sock.bind(("0.0.0.0", p))
                sock.close()
                return True
            except OSError:
                sock.close()
                time.sleep(1)
        return False

    if not wait_for_port(port):
        logger.error(f"連接埠 {port} 持續佔用，無法啟動")
        sys.exit(1)

    from waitress import serve
    logger.info(f"啟動伺服器 0.0.0.0:{port} | PLC {PLC_HOST}:{PLC_PORT}")
    logger.info(f"A箱: {len(BOX_A_CHILLERS)} 冰水機 + {len(BOX_A_DUAL_FANS)} 雙速 + {len(BOX_A_SINGLE_FANS)} 單速 = {len(BOX_A_CHILLERS)+len(BOX_A_DUAL_FANS)+len(BOX_A_SINGLE_FANS)} 設備 (Y0~Y{BOX_A_COIL_COUNT-1})")
    logger.info(f"B箱: {len(BOX_B_FANS)} 雙速 + {len(BOX_B_SINGLES)} 其他 = {len(BOX_B_FANS)+len(BOX_B_SINGLES)} 設備 (Y0~Y{BOX_B_COIL_COUNT-1})")
    sys.stdout.flush()
    serve(app, host="0.0.0.0", port=port, threads=4, channel_timeout=120)
