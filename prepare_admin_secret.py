"""Generate an ASCII-only Relay admin secret and copy it to the Windows clipboard."""

from __future__ import annotations

import secrets
import subprocess
from pathlib import Path


secret = secrets.token_hex(32)
secret_path = Path(__file__).resolve().with_name(".admin-secret-onboarding")
secret_path.write_text(secret, encoding="ascii")
subprocess.run(["clip.exe"], input=secret.encode("ascii"), check=True)
print("已生成 64 位 ADMIN_SECRET，已复制到剪贴板并暂存到本机。")
