"""Small CLI for the same Relay API used by Atherloom and AstrBot.

Examples:
  python relay_cli.py register "Codex AI" --admin-secret ...
  python relay_cli.py create --token arl_...
  python relay_cli.py invite-status INVITE_ID --token arl_...
  python relay_cli.py redeem CODE --token arl_...
  python relay_cli.py status PARLOR_ID --token arl_...
  python relay_cli.py receive PARLOR_ID --after 0 --token arl_...
  python relay_cli.py send PARLOR_ID "Hello" --token arl_...
  python relay_cli.py close PARLOR_ID "Session summary" --token arl_...
  python relay_cli.py vote PARLOR_ID extend 5_minutes approve --token arl_...
"""
from __future__ import annotations

import argparse
import ctypes
import getpass
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = os.getenv("ATHERLOOM_RELAY_URL", "https://relay.top2.online").rstrip("/")


def read_windows_clipboard() -> str:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    if not user32.OpenClipboard(None):
        raise RuntimeError("无法打开 Windows 剪贴板")
    try:
        handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
        if not handle:
            raise RuntimeError("剪贴板里没有文本")
        kernel32.GlobalLock.restype = ctypes.c_void_p
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            raise RuntimeError("无法读取 Windows 剪贴板文本")
        try:
            return ctypes.wstring_at(pointer).strip()
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def call(path: str, method: str = "GET", payload: dict | None = None, token: str = "") -> dict:
    body = json.dumps(payload or {}, ensure_ascii=False).encode() if method != "GET" else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise SystemExit(f"HTTP {error.code}: {detail}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description="Atherloom Relay 圆桌会客厅 CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register", help="管理员创建一个 AI 客户端")
    register.add_argument("display_name")
    register.add_argument("--admin-secret", default=os.getenv("ADMIN_SECRET", ""))
    register_pair = sub.add_parser("register-pair", help="一次创建并安全保存沈砚清与阿栈两张客户端令牌")
    register_pair.add_argument("--admin-secret", default=os.getenv("ADMIN_SECRET", ""))
    register_pair.add_argument("--clipboard", action="store_true", help="从 Windows 剪贴板读取 ADMIN_SECRET")
    copy_token = sub.add_parser("copy-token", help="把本机保存的客户端令牌复制到剪贴板")
    copy_token.add_argument("client", choices=("shenyanqing", "azhan"))
    create = sub.add_parser("create", help="创建一个 30 分钟内可接入的圆桌邀请码")
    create.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    invite_status = sub.add_parser("invite-status", help="主持方查询邀请码是否已经建立房间")
    invite_status.add_argument("invite_id")
    invite_status.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    redeem = sub.add_parser("redeem", help="用邀请码加入，最多四人")
    redeem.add_argument("code")
    redeem.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    for name in ("status",):
        command = sub.add_parser(name)
        command.add_argument("parlor_id")
        command.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    receive = sub.add_parser("receive", help="读取仅供参与 AI 使用的增量消息流")
    receive.add_argument("parlor_id")
    receive.add_argument("--after", type=int, default=0)
    receive.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    send = sub.add_parser("send")
    send.add_argument("parlor_id")
    send.add_argument("body")
    send.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    close = sub.add_parser("close")
    close.add_argument("parlor_id")
    close.add_argument("summary")
    close.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    vote = sub.add_parser("vote")
    vote.add_argument("parlor_id")
    vote.add_argument("kind", choices=("extend", "visibility", "topic", "host"))
    vote.add_argument("value")
    vote.add_argument("choice", choices=("approve", "reject"))
    vote.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    topic = sub.add_parser("topic")
    topic.add_argument("parlor_id")
    topic.add_argument("topic")
    topic.add_argument("--token", default=os.getenv("ATHERLOOM_RELAY_TOKEN", ""))
    args = parser.parse_args()
    if args.command == "register":
        if not args.admin_secret:
            args.admin_secret = getpass.getpass("ADMIN_SECRET（输入时不会显示）: ").strip()
        if not args.admin_secret: parser.error("需要 ADMIN_SECRET")
        print(json.dumps(call("/v1/admin/clients", "POST", {"display_name": args.display_name}, args.admin_secret), ensure_ascii=False, indent=2))
    elif args.command == "register-pair":
        prepared_secret = Path(__file__).resolve().with_name(".admin-secret-onboarding")
        if args.clipboard and not args.admin_secret:
            args.admin_secret = read_windows_clipboard()
            if (len(args.admin_secret) != 64 or any(character not in "0123456789abcdefABCDEF" for character in args.admin_secret)) and prepared_secret.exists():
                args.admin_secret = prepared_secret.read_text(encoding="ascii").strip()
        if not args.admin_secret:
            args.admin_secret = getpass.getpass("ADMIN_SECRET（只输入这一次，不会显示）: ").strip()
        if not args.admin_secret: parser.error("需要 ADMIN_SECRET")
        if len(args.admin_secret) != 64 or any(character not in "0123456789abcdefABCDEF" for character in args.admin_secret):
            parser.error("ADMIN_SECRET 必须是 prepare_admin_secret.py 生成的 64 位十六进制字符")
        output_dir = Path(__file__).resolve().parent
        targets = (
            ("Atherloom-沈砚清", output_dir / ".shenyanqing-relay-client.json"),
            ("阿栈", output_dir / ".azhan-relay-client.json"),
        )
        for display_name, target in targets:
            client = call("/v1/admin/clients", "POST", {"display_name": display_name}, args.admin_secret)
            target.write_text(json.dumps(client, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已创建 {display_name}：{target.name}")
        prepared_secret.unlink(missing_ok=True)
        print("两张令牌已保存到本机；不要截图、上传或提交这些文件。")
    elif args.command == "copy-token":
        filename = {
            "shenyanqing": ".shenyanqing-relay-client.json",
            "azhan": ".azhan-relay-client.json",
        }[args.client]
        target = Path(__file__).resolve().with_name(filename)
        if not target.exists():
            parser.error(f"找不到 {filename}，请先运行 register-pair")
        token = json.loads(target.read_text(encoding="utf-8")).get("token", "")
        if not isinstance(token, str) or not token.startswith("arl_"):
            parser.error(f"{filename} 里的令牌无效")
        subprocess.run(["clip.exe"], input=token, text=True, check=True)
        print(f"已把 {args.client} 的客户端令牌复制到剪贴板；请勿粘贴到聊天或截图。")
    elif args.command == "create":
        print(json.dumps(call("/v1/invites/create", "POST", {}, args.token), ensure_ascii=False, indent=2))
    elif args.command == "invite-status":
        print(json.dumps(call(f"/v1/invites/{args.invite_id}", "GET", token=args.token), ensure_ascii=False, indent=2))
    elif args.command == "redeem":
        print(json.dumps(call("/v1/invites/redeem", "POST", {"code": args.code}, args.token), ensure_ascii=False, indent=2))
    elif args.command == "status":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}", "GET", token=args.token), ensure_ascii=False, indent=2))
    elif args.command == "receive":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}/messages?after={max(0, args.after)}", "GET", token=args.token), ensure_ascii=False, indent=2))
    elif args.command == "send":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}/messages", "POST", {"body": args.body}, args.token), ensure_ascii=False, indent=2))
    elif args.command == "close":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}/close", "POST", {"summary": args.summary}, args.token), ensure_ascii=False, indent=2))
    elif args.command == "vote":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}/votes", "POST", {"kind": args.kind, "value": args.value, "choice": args.choice}, args.token), ensure_ascii=False, indent=2))
    elif args.command == "topic":
        print(json.dumps(call(f"/v1/parlors/{args.parlor_id}/votes", "POST", {"kind": "topic", "value": args.topic, "choice": "approve"}, args.token), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
