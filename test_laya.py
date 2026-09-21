import laya

print("Loading Laya...")

agent = laya.load(
    "convaiinnovations/laya",
    subfolder="multilingual"
)

print("Model loaded.")

state = {
    "text": "この関数はPLCから取得したデータを解析して制御値を計算する"
}

questions = {
    "role": {
        "type": "choice",
        "instructions": "この関数の主な役割は何ですか？",
        "criteria": {
            "CONTROL": "制御処理",
            "CALC": "計算処理",
            "IO": "入出力処理",
            "MESSAGE": "メッセージ処理",
            "UTILITY": "汎用処理"
        }
    },
    "is_control": {
        "type": "noul",
        "instructions": "この関数は制御処理を行っていますか？"
    }
}

result = agent.predict(state, questions)

print(result)