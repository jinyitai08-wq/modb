import os

PLC_HOST = os.environ.get("PLC_HOST", "59.125.52.73")
PLC_PORT = int(os.environ.get("PLC_PORT", "502"))

METER1_SLAVE_ID = int(os.environ.get("METER1_SLAVE_ID", "1"))
METER2_SLAVE_ID = int(os.environ.get("METER2_SLAVE_ID", "2"))
PLC_A_SLAVE_ID = int(os.environ.get("PLC_A_SLAVE_ID", "3"))
PLC_B_SLAVE_ID = int(os.environ.get("PLC_B_SLAVE_ID", "4"))
PLC_TEMP_SLAVE_ID = int(os.environ.get("PLC_TEMP_SLAVE_ID", "3"))

FATEK_Y_OFFSET = 0
FATEK_X_OFFSET = 1000
FATEK_M_OFFSET = 2000
FATEK_R_OFFSET = 0
FATEK_D_OFFSET = 6000
FATEK_T_REG_OFFSET = 9000
FATEK_C_REG_OFFSET = 9500


def fatek_d_addr(d_num):
    return FATEK_D_OFFSET + d_num


def fatek_r_addr(r_num):
    return FATEK_R_OFFSET + r_num


def fatek_y_addr(y_num):
    return FATEK_Y_OFFSET + y_num


METER1_BASE_R = 0
METER2_BASE_R = 100

METER_CT_RATIO = "400:5A"

METER1_PARAMS = [
    {"offset": 4, "name": "電壓", "unit": "V", "group": "電壓"},
    {"offset": 42, "name": "平均電壓", "unit": "V", "group": "電壓"},
    {"offset": 6, "name": "L1 電流", "unit": "A", "group": "電流"},
    {"offset": 8, "name": "L2 電流", "unit": "A", "group": "電流"},
    {"offset": 10, "name": "L3 電流", "unit": "A", "group": "電流"},
    {"offset": 46, "name": "平均電流", "unit": "A", "group": "電流"},
    {"offset": 12, "name": "L1 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 14, "name": "L2 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 16, "name": "L3 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 52, "name": "總功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 30, "name": "L1 PF", "unit": "", "group": "功率因數"},
    {"offset": 32, "name": "L2 PF", "unit": "", "group": "功率因數"},
    {"offset": 34, "name": "L3 PF", "unit": "", "group": "功率因數"},
    {"offset": 62, "name": "總 PF", "unit": "", "group": "功率因數"},
]

METER2_PARAMS = [
    {"offset": 0, "name": "L1-N 電壓", "unit": "V", "group": "電壓"},
    {"offset": 2, "name": "L2-N 電壓", "unit": "V", "group": "電壓"},
    {"offset": 4, "name": "L3-N 電壓", "unit": "V", "group": "電壓"},
    {"offset": 42, "name": "平均電壓", "unit": "V", "group": "電壓"},
    {"offset": 6, "name": "L1 電流", "unit": "A", "group": "電流"},
    {"offset": 8, "name": "L2 電流", "unit": "A", "group": "電流"},
    {"offset": 10, "name": "L3 電流", "unit": "A", "group": "電流"},
    {"offset": 46, "name": "平均電流", "unit": "A", "group": "電流"},
    {"offset": 12, "name": "L1 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 14, "name": "L2 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 16, "name": "L3 功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 52, "name": "總功率", "unit": "kW", "group": "功率", "div": 1000},
    {"offset": 30, "name": "L1 PF", "unit": "", "group": "功率因數"},
    {"offset": 32, "name": "L2 PF", "unit": "", "group": "功率因數"},
    {"offset": 34, "name": "L3 PF", "unit": "", "group": "功率因數"},
    {"offset": 62, "name": "總 PF", "unit": "", "group": "功率因數"},
]

METER_READ_COUNT = 68

TEMP_R_REG = int(os.environ.get("TEMP_R_REG", "1000"))
TEMP_COUNT = int(os.environ.get("TEMP_COUNT", "12"))
TEMP_ADDRESS = fatek_r_addr(TEMP_R_REG)

BOX_A_CHILLERS = [
    {"y": fatek_y_addr(0), "name": "冰水機1"},
    {"y": fatek_y_addr(1), "name": "冰水機2"},
]

BOX_A_DUAL_FANS = [
    {"y_l": fatek_y_addr(2), "y_h": fatek_y_addr(3), "name": "新娘休息室送風機"},
    {"y_l": fatek_y_addr(38), "y_h": fatek_y_addr(39), "name": "壽司吧左前送風機"},
    {"y_l": fatek_y_addr(40), "y_h": fatek_y_addr(41), "name": "壽司吧右前送風機"},
    {"y_l": fatek_y_addr(42), "y_h": fatek_y_addr(43), "name": "壽司吧左側送風機"},
    {"y_l": fatek_y_addr(44), "y_h": fatek_y_addr(45), "name": "壽司吧右側送風機"},
    {"y_l": fatek_y_addr(46), "y_h": fatek_y_addr(47), "name": "小吃區右左送風機"},
    {"y_l": fatek_y_addr(48), "y_h": fatek_y_addr(49), "name": "石洗碗區送風機"},
    {"y_l": fatek_y_addr(50), "y_h": fatek_y_addr(51), "name": "廁所送風機"},
    {"y_l": fatek_y_addr(52), "y_h": fatek_y_addr(53), "name": "大廳送風機"},
    {"y_l": fatek_y_addr(54), "y_h": fatek_y_addr(55), "name": "包廂櫃台走道送風機"},
    {"y_l": fatek_y_addr(56), "y_h": fatek_y_addr(57), "name": "廁所前走道送風機"},
    {"y_l": fatek_y_addr(58), "y_h": fatek_y_addr(59), "name": "舞洗碗區送風機"},
    {"y_l": fatek_y_addr(60), "y_h": fatek_y_addr(61), "name": "廚房後送風機"},
    {"y_l": fatek_y_addr(62), "y_h": fatek_y_addr(63), "name": "廚房前送風機"},
]

BOX_A_SINGLE_FANS = [
    {"y": fatek_y_addr(4), "name": "大美送風機"},
    {"y": fatek_y_addr(6), "name": "清風送風機"},
    {"y": fatek_y_addr(8), "name": "水月1送風機"},
    {"y": fatek_y_addr(10), "name": "水月2送風機"},
    {"y": fatek_y_addr(12), "name": "舞雪送風機"},
    {"y": fatek_y_addr(14), "name": "如雲送風機"},
    {"y": fatek_y_addr(16), "name": "初日送風機"},
    {"y": fatek_y_addr(18), "name": "澄淨送風機"},
    {"y": fatek_y_addr(20), "name": "歸真送風機"},
    {"y": fatek_y_addr(22), "name": "小雅送風機"},
    {"y": fatek_y_addr(32), "name": "千江1送風機"},
    {"y": fatek_y_addr(34), "name": "千江2送風機"},
    {"y": fatek_y_addr(36), "name": "千江3送風機"},
]

BOX_A_COIL_COUNT = 64

BOX_B_FANS = [
    {"y_l": fatek_y_addr(0), "y_h": fatek_y_addr(1), "name": "廚房送風機"},
    {"y_l": fatek_y_addr(2), "y_h": fatek_y_addr(3), "name": "工作區送風機"},
    {"y_l": fatek_y_addr(4), "y_h": fatek_y_addr(5), "name": "咖啡吧送風機"},
    {"y_l": fatek_y_addr(6), "y_h": fatek_y_addr(7), "name": "排排坐1.2送風機"},
    {"y_l": fatek_y_addr(8), "y_h": fatek_y_addr(9), "name": "廁所前1.2送風機"},
    {"y_l": fatek_y_addr(10), "y_h": fatek_y_addr(11), "name": "高腳椅送風機"},
    {"y_l": fatek_y_addr(12), "y_h": fatek_y_addr(13), "name": "1區後送風機"},
    {"y_l": fatek_y_addr(14), "y_h": fatek_y_addr(15), "name": "1區前送風機"},
    {"y_l": fatek_y_addr(16), "y_h": fatek_y_addr(17), "name": "大廳送風機"},
    {"y_l": fatek_y_addr(18), "y_h": fatek_y_addr(19), "name": "半圓沙發前送風機"},
    {"y_l": fatek_y_addr(20), "y_h": fatek_y_addr(21), "name": "半圓沙發後送風機"},
    {"y_l": fatek_y_addr(22), "y_h": fatek_y_addr(23), "name": "玻璃屋中送風機"},
    {"y_l": fatek_y_addr(24), "y_h": fatek_y_addr(25), "name": "玻璃屋後送風機"},
    {"y_l": fatek_y_addr(26), "y_h": fatek_y_addr(27), "name": "玻璃屋前送風機"},
]

BOX_B_SINGLES = [
    {"y": fatek_y_addr(28), "name": "燈光總盤"},
]

BOX_B_COIL_COUNT = 29
