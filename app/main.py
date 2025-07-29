"""Susanoo.

See: https://github.com/kwcplus/susanoo
"""

import logging
from typing import Annotated

from call import Call
from fastapi import Body, FastAPI, HTTPException, Query
from mangum import Mangum
from models import CallParams, Settings
from session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(funcName)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = Settings()
session_manager = SessionManager(settings)
call = Call(settings)
app = FastAPI(
    debug=True,
    title="Susanoo",
    description="See [https://github.com/kwcplus/susanoo](https://github.com/kwcplus/susanoo)",
)


def create_call(session_id: str):
    try:
        session = session_manager.read(session_id)
    except ValueError as e:
        # session_id が見つからない理由のほとんどは架電終了
        return {"message": f"session not found. the call has probably ended: {e}"}

    if len(session.to_list) == 0:
        return {"message": f"no more calls: {session_id}"}

    to = Call.to_e164(session.to_list.pop(0))
    from_ = settings.vonage_number

    # https://developer.vonage.com/en/voice/voice-api/ncco-reference
    ncco = [
        {
            "action": "talk",
            "text": "応答するには 1 を押してください。応答できない場合は 9 など 1 以外の数字を押してください",
            "language": "ja-JP",
            "bargeIn": True,
        },
        {
            "action": "input",
            "type": ["dtmf"],
            "dtmf": {
                "maxDigits": 1,
                "timeOut": 5,
                "submitOnHash": True,
            },
            "eventUrl": [
                settings.susanoo_url + "/input/" + session_id,
            ],
        },
    ]

    event_url = settings.susanoo_url + "/event/" + session_id

    result = call.create(to=to, from_=from_, ncco=ncco, event_url=event_url)
    session_manager.update(session_id, session.to_list)

    return {"message": f"create call: {result}"}


# Annotated[CallParams, Body()] にしたいが、Mackerel のように URL パラメータしか指定できず、
# CallParams に合致しない Body を送る場合があるため dict を使う
@app.post("/")
async def incoming_webhook(
    body: Annotated[dict, Body()] = None,
    to: Annotated[str, Query()] = None,
    text: Annotated[str, Query()] = None,
    loop: Annotated[int, Query()] = 3,
    round_robin: Annotated[bool, Query()] = True,
):
    """Zabbix や Mackerel から呼び出されて電話発信."""
    # Mackerel のように URL パラメータしか指定できず、Body も送る場合があるため Query を優先
    if to and text:
        call_params = CallParams(to=to, text=text, loop=loop, round_robin=round_robin)
    elif "to" not in body or "text" not in body:
        raise HTTPException(
            status_code=400,
            detail="to と text パラメータが必要です: https://github.com/kwcplus/susanoo",
        )
    else:
        call_params = CallParams(
            to=body["to"],
            text=body["text"],
            loop=body.get("loop", 3),
            round_robin=body.get("round_robin", True),
        )

    numbers = call_params.to.split(",")
    invalid_numbers = [number for number in numbers if not Call.validate_number(number)]

    if invalid_numbers:
        raise HTTPException(
            status_code=400,
            detail=f"電話番号の形式が正しくありません。見直してください: {invalid_numbers}",
        )

    try:
        session_id = session_manager.create(call_params)
        return create_call(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/event/{session_id}")
async def event(session_id: str, data: dict = Body(...)):
    logger.info(f"POST /event/{session_id}: {data}")
    if "status" in data:
        if data["status"] == "completed":
            return create_call(session_id)
    return {"message": f"unknown event: {session_id} {data}"}


@app.post("/input/{session_id}")
async def input(session_id: str, data: dict = Body(...)):
    logger.info(f"POST /input/{session_id}: {data}")
    session = session_manager.read(session_id)
    if "dtmf" in data:
        if "digits" in data["dtmf"]:
            if data["dtmf"]["digits"] == "1":
                # 応答したため、これ以上の架電は不要。そのためデータ削除
                session_manager.delete(session_id)
                return [
                    {
                        "action": "talk",
                        "text": session.call_params.text,
                        "language": "ja-JP",
                    }
                ]
            # どんなコールも /event に completed になるため、/event で架電させる
            # しかし、応答していた場合はセッションがないため発信先がないため終了する
            return {"message": f"next call: {session_id}"}

    raise HTTPException(status_code=500, detail=f"input error: {data}")


handler = Mangum(app, lifespan="off")
