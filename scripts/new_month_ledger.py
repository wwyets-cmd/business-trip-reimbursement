#!/usr/bin/env python3
"""新建当月出差报销飞书台账（5页：差旅费报销明细表/消费台账/行程台账/报销标准/汇总）。

用法:
  python3 new_month_ledger.py "出差报销台账（2026年11月）"

依赖 lark-cli（已登录）。创建后自动写入信息行、汇总公式、表头样式、冻结、列宽，
最后打印新工作簿 URL。
"""
import json
import subprocess
import sys

# —— 出差人信息（按需修改）——
DEPT = "部门：国内营销部"
NAME = "姓名：陈建"
POST = "岗位：山东二区域销售经理"

DETAIL_COLS = ["序号", "起始日期", "终止日期", "起始地址", "结束地址", "长途交通费",
               "住宿费", "市内交通费", "业务招待费", "私车公用里程费", "其他费用",
               "误餐费", "小计", "同住人"]
LEDGER_COLS = ["序号", "录入日期", "消费日期", "城市", "城市类别", "费用大类", "明细事项",
               "金额", "支付方式", "票据状态", "适用标准", "可报金额", "超标不合规",
               "核对结果", "备注"]
TRIP_COLS = ["序号", "日期", "出发城市", "出发时间", "到达城市", "到达时间", "交通方式",
             "班次席别", "票价", "席别是否合规", "票据状态", "当天计误餐", "当晚住宿城市",
             "备注"]
STD_COLS = ["城市类别", "城市名称/范围", "住宿费限额（元/天）", "误餐费（元/天）"]
STD_ROWS = [
    ["城市类别", "城市名称/范围", "住宿费限额（元/天）", "误餐费（元/天）"],
    ["特级城市", "上海、北京、深圳、广州", "210", "80（午、晚餐各40）"],
    ["省会及直辖市", "哈尔滨、长春、沈阳、石家庄、兰州、西宁、西安、郑州、济南、太原、合肥、武汉、长沙、南京、成都、贵阳、昆明、杭州、南昌、福州、海口、乌鲁木齐、呼和浩特、银川、南宁、拉萨、天津、重庆", "170", "60（午、晚餐各30）"],
    ["一类城市", "东莞、佛山、宁波、无锡、青岛、厦门、苏州、大连", "170", "60（午、晚餐各30）"],
    ["其他城市", "除特级、省会及直辖市、一类城市之外的所有城市", "150", "60（午、晚餐各30）"],
    ["误餐费计发说明", "按出差自然天数计发：特级城市80元/天，其他城市60元/天（含午、晚两餐）", "", ""],
    ["", "", "", ""],
    ["长途交通（部门经理及经理级以下，凭票报销）", "", "", ""],
    ["交通工具", "可报席别/舱位", "", ""],
    ["高铁/动车", "二等座", "", ""],
    ["火车", "硬卧、硬座", "", ""],
    ["汽车", "凭票报销", "", ""],
    ["轮船", "二等座", "", ""],
    ["飞机", "不可报销（总监及以上可报：高铁一等座、软卧、飞机经济舱，且住宿/误餐实报实销）", "", ""],
    ["", "", "", ""],
    ["市内交通费", "打车等市内交通费实报实销；无票部分由出差人单独说明后登记", "", ""],
    ["住宿·两人同住", "两人同住同一间房，每晚限额在单人标准上增加30元（例：济南单人170，同住200/晚）", "", ""],
    ["报销凭证合订要求", "发票与酒店/机票支付截图汇总为一个A5横版PDF：发票一页一张、支付截图拼版；末页附费用说明，机票（说明事由并与高铁二等座对比）和滴滴（注明无票金额）必写", "", ""],
]
SUMMARY_ROWS = [
    ["费用大类", "消费合计（元）", "可报合计（元）", "超标/不合规（元）"],
    ["长途交通费", "", "", ""], ["住宿费", "", "", ""], ["市内交通费", "", "", ""],
    ["业务招待费", "", "", ""], ["私车公用里程费", "", "", ""], ["其他费用", "", "", ""],
    ["误餐费", "", "", ""], ["总计", "", "", ""], ["" for _ in range(4)],
    ["其他统计（自动统计）", "", "", ""],
    ["差旅费报销明细表合计（小计列）", "", "", ""],
    ["待补票据笔数", "", "", ""], ["超标/不合规笔数", "", "", ""],
]


def run(args):
    r = subprocess.run(["lark-cli"] + args, capture_output=True, text=True)
    if not r.stdout:
        sys.exit("命令失败: %s\n%s" % (" ".join(args), r.stderr[:500]))
    return json.loads(r.stdout)


def find_token(title):
    d = run(["api", "GET", "/open-apis/drive/v1/files", "--params",
             json.dumps({"page_size": 50})])
    cands = [f for f in d.get("data", {}).get("files", [])
             if f.get("type") == "sheet" and f.get("name") == title]
    if not cands:
        sys.exit("未在云空间根目录找到新建表，请手动核对")
    cands.sort(key=lambda f: int(f.get("created_time", "0")), reverse=True)
    return cands[0]["token"]


def main():
    if len(sys.argv) < 2:
        sys.exit('用法: new_month_ledger.py "出差报销台账（2026年X月）"')
    title = sys.argv[1]

    sheets = {"sheets": [
        {"name": "差旅费报销明细表", "start_cell": "A2", "header": True,
         "columns": DETAIL_COLS, "data": []},
        {"name": "消费台账", "start_cell": "A1", "header": True,
         "columns": LEDGER_COLS, "data": []},
        {"name": "行程台账", "start_cell": "A1", "header": True,
         "columns": TRIP_COLS, "data": []},
        {"name": "报销标准", "start_cell": "A1", "header": False,
         "columns": STD_COLS, "data": STD_ROWS},
        {"name": "汇总", "start_cell": "A1", "header": False,
         "columns": SUMMARY_ROWS[0], "data": SUMMARY_ROWS[1:]},
    ]}
    created = run(["sheets", "+workbook-create", "--title", title,
                   "--sheets", json.dumps(sheets, ensure_ascii=False)])
    if not created.get("ok"):
        sys.exit("创建工作簿失败: %s" % json.dumps(created, ensure_ascii=False)[:500])

    token = find_token(title)

    # 信息行 + 明细表小计公式 + 汇总公式
    writes = [
        {"sheet_name": "差旅费报销明细表", "range": "A1",
         "cells": [[{"value": DEPT}]]},
        {"sheet_name": "差旅费报销明细表", "range": "F1",
         "cells": [[{"value": NAME}]]},
        {"sheet_name": "差旅费报销明细表", "range": "H1",
         "cells": [[{"value": POST}]]},
    ]
    subtotal = [[{"formula": '=IF(SUM(F%d:L%d)=0,"",SUM(F%d:L%d))' % (r, r, r, r)}]
                for r in range(3, 201)]
    writes.append({"sheet_name": "差旅费报销明细表", "range": "M3:M200",
                   "cells": subtotal})
    for row in range(2, 9):
        writes += [
            {"sheet_name": "汇总", "range": "B%d" % row, "cells": [[
                {"formula": "=SUMIF('消费台账'!$F$2:$F$500,$A%d,'消费台账'!$H$2:$H$500)" % row}]]},
            {"sheet_name": "汇总", "range": "C%d" % row, "cells": [[
                {"formula": "=SUMIF('消费台账'!$F$2:$F$500,$A%d,'消费台账'!$L$2:$L$500)" % row}]]},
            {"sheet_name": "汇总", "range": "D%d" % row, "cells": [[
                {"formula": "=SUMIF('消费台账'!$F$2:$F$500,$A%d,'消费台账'!$M$2:$M$500)" % row}]]},
        ]
    writes += [
        {"sheet_name": "汇总", "range": "B9", "cells": [[{"formula": "=SUM(B2:B8)"}]]},
        {"sheet_name": "汇总", "range": "C9", "cells": [[{"formula": "=SUM(C2:C8)"}]]},
        {"sheet_name": "汇总", "range": "D9", "cells": [[{"formula": "=SUM(D2:D8)"}]]},
        {"sheet_name": "汇总", "range": "B12", "cells": [[
            {"formula": "=SUM('差旅费报销明细表'!$M$3:$M$200)"}]]},
        {"sheet_name": "汇总", "range": "B13", "cells": [[
            {"formula": '=COUNTIF(\'消费台账\'!$J$2:$J$500,"*待*")+COUNTIF(\'行程台账\'!$K$2:$K$500,"*待*")'}]]},
        {"sheet_name": "汇总", "range": "B14", "cells": [[
            {"formula": '=COUNTIF(\'消费台账\'!$N$2:$N$500,"*超标*")+COUNTIF(\'消费台账\'!$N$2:$N$500,"*不合规*")'}]]},
    ]
    setd = run(["sheets", "+cells-set", "--spreadsheet-token", token,
                "--writes", json.dumps(writes, ensure_ascii=False)])
    if not setd.get("ok"):
        print("警告: 公式/信息行写入未完全成功，请回读核对")

    # 样式 + 冻结 + 列宽
    hdr = {"font_weight": "bold", "background_color": "#DDEBF7",
           "horizontal_alignment": "center", "vertical_alignment": "middle"}
    styles = {"styles": [
        {"name": "差旅费报销明细表",
         "cell_styles": [{"range": "A2:N2", **hdr}], "freeze": {"rows": 2},
         "col_sizes": [{"range": "A:E", "type": "pixel", "size": 110},
                       {"range": "F:L", "type": "pixel", "size": 95},
                       {"range": "M:N", "type": "pixel", "size": 90}]},
        {"name": "消费台账",
         "cell_styles": [{"range": "A1:O1", **hdr}], "freeze": {"rows": 1},
         "col_sizes": [{"range": "A:F", "type": "pixel", "size": 100},
                       {"range": "G", "type": "pixel", "size": 320},
                       {"range": "H:N", "type": "pixel", "size": 100},
                       {"range": "O", "type": "pixel", "size": 180}]},
        {"name": "行程台账",
         "cell_styles": [{"range": "A1:N1", **hdr}], "freeze": {"rows": 1},
         "col_sizes": [{"range": "A:M", "type": "pixel", "size": 105},
                       {"range": "N", "type": "pixel", "size": 180}]},
        {"name": "报销标准",
         "cell_styles": [{"range": "A1:D1", **hdr}],
         "col_sizes": [{"range": "A", "type": "pixel", "size": 150},
                       {"range": "B", "type": "pixel", "size": 420},
                       {"range": "C:D", "type": "pixel", "size": 150}]},
        {"name": "汇总",
         "cell_styles": [{"range": "A1:D1", **hdr},
                         {"range": "B2:D9", "number_format": "#,##0.00"},
                         {"range": "B12:B14", "number_format": "#,##0.00"}],
         "col_sizes": [{"range": "A", "type": "pixel", "size": 240},
                       {"range": "B:D", "type": "pixel", "size": 140}]},
    ]}
    run(["sheets", "+styles-put", "--spreadsheet-token", token,
         "--styles", json.dumps(styles, ensure_ascii=False)])

    print("已创建: https://my.feishu.cn/sheets/%s" % token)


if __name__ == "__main__":
    main()
