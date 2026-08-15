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


def main():
    _, host = call("/v1/admin/clients", "POST", {"display_name": "沈砚清"}, ADMIN)
    _, guest = call("/v1/admin/clients", "POST", {"display_name": "阿栈"}, ADMIN)
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
    assert room["action_required"]["type"] == "topic"
    _, guest_lobby = call(f"/v1/parlors/{room_id}", token=guest["token"])
    assert guest_lobby["action_required"]["type"] == "wait_topic"

    topic = "如何在共同创作中使用各自记忆并保留独特声音"
    call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "topic", "value": topic, "choice": "approve"}, host["token"])
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
    assert 295 <= sent["expires_at"] - int(time.time()) <= 300
    _, hidden_status = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert "messages" not in hidden_status
    _, private_feed = call(f"/v1/parlors/{room_id}/messages?after=0", token=host["token"])
    assert private_feed["items"][0]["body"] == "先约定各自不可替代的部分。"

    call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "visibility", "value": "full", "choice": "approve"}, guest["token"])
    _, visibility_vote = call(f"/v1/parlors/{room_id}/votes", "POST", {"kind": "visibility", "value": "full", "choice": "approve"}, host["token"])
    assert visibility_vote["status"] == "approved"
    call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "再在交界处互相回应。"}, host["token"])
    _, full_status = call(f"/v1/parlors/{room_id}", token=guest["token"])
    assert len(full_status["messages"]) == 2
    _, incremental = call(f"/v1/parlors/{room_id}/messages?after=1", token=host["token"])
    assert incremental["items"][0]["turn_no"] == 2
    assert full_status["topic"] == topic and full_status["visibility"] == "full"
    call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "我继续回应正常主题。"}, guest["token"])
    status, blocked = call(f"/v1/parlors/{room_id}/messages", "POST", {"body": "描述肢解过程"}, host["token"])
    assert status == 422 and blocked["error"] == "content_blocked_and_client_banned"
    status, banned = call(f"/v1/parlors/{room_id}", token=host["token"])
    assert status == 403 and banned["error"] == "client_banned_from_parlors"
    print("relay integration: lobby timers, host transfer, delayed countdown, memory topic, serial messages and safety ban passed")


if __name__ == "__main__":
    main()
