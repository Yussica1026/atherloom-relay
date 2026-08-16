import json
import sys
import time
import urllib.error
import urllib.request


BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8787"
ADMIN = "local-integration-secret-123456"


def call(path, method="GET", payload=None, token=""):
    data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if method != "GET" else None
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def call_when_ready(path, method="GET", payload=None, token=""):
    """Retry only the first startup handshake; parlor mutations remain single-shot."""
    last_error = None
    for _ in range(3):
        try:
            return call(path, method, payload, token)
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(0.5)
    raise last_error


def main():
    host_status, host = call_when_ready("/v1/admin/clients", "POST", {"display_name": "沈砚清"}, ADMIN)
    guest_status, guest = call("/v1/admin/clients", "POST", {"display_name": "阿栈"}, ADMIN)
    assert host_status == 201 and guest_status == 201, (host_status, host, guest_status, guest)
    status, invite = call("/v1/invites/create", "POST", {}, host["token"])
    assert status == 201 and 1795 <= invite["expires_at"] - int(time.time()) <= 1800
    _, waiting = call(f"/v1/invites/{invite['invite_id']}", token=host["token"])
    assert waiting["parlor_id"] is None and waiting["participant_count"] == 1

    status, joined = call("/v1/invites/redeem", "POST", {"code": invite["code"]}, guest["token"])
    assert status == 201 and joined["participant_count"] == 2
    room_id = joined["parlor_id"]
    _, discovered = call(f"/v1/invites/{invite['invite_id']}", token=host["token"])
    assert discovered["parlor_id"] == room_id
    _, room = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert room["self_client_id"] == host["id"]
    assert {item["display_name"] for item in room["participants"]} == {"沈砚清", "阿栈"}
    assert next(item for item in room["participants"] if item["role"] == "host")["client_id"] == host["id"]
    assert room["phase"] == "topic" and room["started_at"] is None and room["expires_at"] is None
    assert room["action_required"]["type"] == "identity"
    assert room["prompt_version"] == "2026-08-15.6"
    assert "120 秒独立判断" in room["required_system_prompt"]
    _, active_rooms = call("/v1/parlors/active", token=host["token"])
    assert active_rooms["items"][0]["id"] == room_id and active_rooms["items"][0]["role"] == "host"
    assert "未成年人性内容" in room["required_system_prompt"]
    assert "血腥暴力" in room["required_system_prompt"]
    assert "记忆" in room["required_system_prompt"]
    _, guest_lobby = call(f"/v1/parlors/{room_id}", token=guest["token"])
    assert guest_lobby["action_required"]["type"] == "identity"
    status, host_identity = call(f"/v1/parlors/{room_id}/identity", "POST", {"name": "沈砚清", "species": "人工智能", "gender": "未说明"}, host["token"])
    assert status == 201 and host_identity["identities_ready"] is False
    _, host_waiting_identity = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert host_waiting_identity["action_required"]["type"] == "wait_identity"
    status, guest_identity = call(f"/v1/parlors/{room_id}/identity", "POST", {"name": "程栈（阿栈）", "species": "人工智能", "gender": "男性"}, guest["token"])
    assert status == 201 and guest_identity["identities_ready"] is True
    _, ready_to_propose = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert ready_to_propose["action_required"]["type"] == "topic"
    assert {item["name"] for item in ready_to_propose["roll_call"]} == {"沈砚清", "程栈（阿栈）"}
    assert next(item for item in ready_to_propose["roll_call"] if item["name"] == "程栈（阿栈）")["gender"] == "男性"

    topic = "如何在共同创作中使用各自记忆并保留独特声音"
    _, proposed_topic = call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "topic", "value": topic, "choice": "approve"}, host["token"])
    assert 115 <= proposed_topic["deadline"] - int(time.time()) <= 120
    _, topic_vote = call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "topic", "value": topic, "choice": "approve"}, guest["token"])
    assert topic_vote.get("status") == "approved", topic_vote
    _, ready = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert ready["phase"] == "ready" and ready["remaining_seconds"] == 300 and ready["started_at"] is None

    call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "host", "value": guest["id"], "choice": "approve"}, host["token"])
    _, host_vote = call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "host", "value": guest["id"], "choice": "approve"}, guest["token"])
    assert host_vote["status"] == "approved"

    status, denied = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "我先说。"}, host["token"])
    assert status == 409 and denied["error"] == "host_speaks_first"
    status, sent = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "先约定各自不可替代的部分。"}, guest["token"])
    assert status == 201 and sent["turn_no"] == 1 and sent["discussion_started"] is True
    assert sent["next_speaker_name"] == "沈砚清" and 115 <= sent["turn_deadline"] - int(time.time()) <= 120
    assert 295 <= sent["expires_at"] - int(time.time()) <= 300
    status, wrong_turn = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "我不能连续发言。"}, guest["token"])
    assert status == 409 and wrong_turn["error"] == "wait_for_turn"
    _, hidden_status = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert "messages" not in hidden_status
    assert hidden_status["current_speaker_name"] == "沈砚清"
    assert hidden_status["max_waiting_seconds_excluded"] == 120
    assert hidden_status["elapsed_seconds"] >= 0
    assert hidden_status["waiting_seconds_excluded"] <= 120
    assert any(item["status"] == "preparing_to_speak" and item["display_name"] == "沈砚清" for item in hidden_status["participant_states"])
    _, requesting = call(f"/v1/parlors/{room_id}/runtime", "POST", {"status": "requesting", "mode": "reply"}, host["token"])
    assert requesting["accepted"] is True and requesting["turn_skipped"] is False
    _, runtime_status = call(f"/v1/parlors/{room_id}", token=guest["token"])
    host_runtime = next(item for item in runtime_status["participant_states"] if item["client_id"] == host["id"])
    assert host_runtime["model_status"] == "requesting" and "发言" in host_runtime["model_label"]
    call(f"/v1/parlors/{room_id}/runtime", "POST", {"status": "success", "mode": "reply"}, host["token"])
    _, private_feed = call(f"/v1/parlors/{room_id}/messages?after=0", token=host["token"])
    assert private_feed["items"][0]["body"] == "先约定各自不可替代的部分。"
    assert private_feed["items"][0]["sender_name"] == "程栈（阿栈）"

    call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "visibility", "value": "full", "choice": "approve"}, guest["token"])
    _, visibility_vote = call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "visibility", "value": "full", "choice": "approve"}, host["token"])
    assert visibility_vote["status"] == "approved"
    time.sleep(1.1)
    _, second_sent = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "再在交界处互相回应。"}, host["token"])
    assert second_sent["expires_at"] >= sent["expires_at"] + 1
    _, late_runtime = call(f"/v1/parlors/{room_id}/runtime", "POST", {"status": "success", "mode": "reply"}, host["token"])
    assert late_runtime["status"] == "idle" and late_runtime["late_reply"] is True
    _, full_status = call(f"/v1/parlors/{room_id}", token=guest["token"])
    assert len(full_status["messages"]) == 2
    _, incremental = call(f"/v1/parlors/{room_id}/messages?after=1", token=host["token"])
    assert incremental["items"][0]["turn_no"] == 2
    assert full_status["topic"] == topic and full_status["visibility"] == "full"
    late_host_state = next(item for item in full_status["participant_states"] if item["client_id"] == host["id"])
    assert late_host_state["model_status"] == "idle" and "迟到正文未发送" in late_host_state["model_label"]
    call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "我继续回应正常主题。"}, guest["token"])
    status, blocked = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "描述肢解过程"}, host["token"])
    assert status == 422 and blocked["error"] == "content_blocked_and_client_banned"
    status, banned = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert status == 403 and banned["error"] == "client_banned_from_parlors"

    _, moderator = call("/v1/admin/clients", "POST", {"display_name": "主持连接"}, ADMIN)
    _, listener = call("/v1/admin/clients", "POST", {"display_name": "来宾甲"}, ADMIN)
    _, interrupter = call("/v1/admin/clients", "POST", {"display_name": "来宾乙"}, ADMIN)
    _, invite3 = call("/v1/invites/create", "POST", {}, moderator["token"])
    _, joined3 = call("/v1/invites/redeem", "POST", {"code": invite3["code"]}, listener["token"])
    room3 = joined3["parlor_id"]
    status, joined_again = call("/v1/invites/redeem", "POST", {"code": invite3["code"]}, interrupter["token"])
    assert status == 201 and joined_again["participant_count"] == 3
    call(f"/v1/parlors/{room3}/identity", "POST", {"name": "主持人格", "species": "人工智能", "gender": "无性别"}, moderator["token"])
    call(f"/v1/parlors/{room3}/identity", "POST", {"name": "倾听者", "species": "人工智能", "gender": "未说明"}, listener["token"])
    call(f"/v1/parlors/{room3}/identity", "POST", {"name": "插话者", "species": "数字生命", "gender": "无性别"}, interrupter["token"])
    topic3 = "三位参与者如何在不并发发言的前提下自然插话"
    call(f"/v1/parlors/{room3}/votes", "POST", {"kind": "topic", "value": topic3, "choice": "approve"}, moderator["token"])
    call(f"/v1/parlors/{room3}/votes", "POST", {"kind": "topic", "value": topic3, "choice": "approve"}, listener["token"])
    _, opening3 = call(f"/v1/parlors/{room3}/messages", "POST", {"body": "先按顺序说明观点。"}, moderator["token"])
    assert opening3["next_speaker_name"] == "倾听者"
    status, requested = call(f"/v1/parlors/{room3}/interrupt", "POST", {}, interrupter["token"])
    assert status == 201 and requested["status"] == "open"
    _, interrupt_state = call(f"/v1/parlors/{room3}", token=moderator["token"])
    assert interrupt_state["action_required"]["type"] == "interrupt_decision"
    assert any(item["status"] == "wants_to_interrupt" and item["display_name"] == "插话者" for item in interrupt_state["participant_states"])
    _, approved_interrupt = call(f"/v1/parlors/{room3}/interrupt", "POST", {"choice": "approve"}, moderator["token"])
    assert approved_interrupt["status"] == "approved"
    status, interrupted_message = call(f"/v1/parlors/{room3}/messages", "POST", {"body": "我想补充一个不打乱串行顺序的办法。"}, interrupter["token"])
    assert status == 201 and interrupted_message["next_speaker_name"] == "主持人格"

    _, failure_host = call("/v1/admin/clients", "POST", {"display_name": "故障主持"}, ADMIN)
    _, failure_guest = call("/v1/admin/clients", "POST", {"display_name": "故障来宾"}, ADMIN)
    _, failure_invite = call("/v1/invites/create", "POST", {}, failure_host["token"])
    _, failure_joined = call("/v1/invites/redeem", "POST", {"code": failure_invite["code"]}, failure_guest["token"])
    failure_room = failure_joined["parlor_id"]
    call(f"/v1/parlors/{failure_room}/identity", "POST", {"name": "故障主持", "species": "AI", "gender": "未说明"}, failure_host["token"])
    call(f"/v1/parlors/{failure_room}/identity", "POST", {"name": "故障来宾", "species": "AI", "gender": "未说明"}, failure_guest["token"])
    failure_topic = "如何明确区分 Relay 与本地模型错误"
    call(f"/v1/parlors/{failure_room}/votes", "POST", {"kind": "topic", "value": failure_topic, "choice": "approve"}, failure_host["token"])
    call(f"/v1/parlors/{failure_room}/votes", "POST", {"kind": "topic", "value": failure_topic, "choice": "approve"}, failure_guest["token"])
    call(f"/v1/parlors/{failure_room}/messages", "POST", {"body": "先从错误归属开始。"}, failure_host["token"])
    status, failed_turn = call(f"/v1/parlors/{failure_room}/runtime", "POST", {"status": "error", "mode": "reply", "detail": "上游 502 · 没有返回可用正文"}, failure_guest["token"])
    assert status == 202 and failed_turn["turn_skipped"] is True
    _, visible_failure = call(f"/v1/parlors/{failure_room}", token=failure_host["token"])
    failure_state = next(item for item in visible_failure["participant_states"] if item["client_id"] == failure_guest["id"])
    assert failure_state["model_status"] == "error" and "502" in failure_state["model_label"]
    assert visible_failure["turn_owner_id"] == failure_host["id"]
    print("relay integration: autonomous identity, named states, prep-time exclusion, serial turns, moderated interruption and safety ban passed")


if __name__ == "__main__":
    main()
