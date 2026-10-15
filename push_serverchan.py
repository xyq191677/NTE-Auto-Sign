#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
塔吉多(异环) 签到结果 -> 微信(Server酱) 推送脚本（零依赖版）
配合 auto-sign.yml 使用：上一步会把 nte.py 的输出 tee 到 sign.log，
本脚本读取 sign.log 并推送到 Server酱。

配置：在仓库 Settings -> Secrets 里建 SERVERCHAN_KEY（值为 sct.ftqq.com 的 SCT... SendKey）。
未配置则只打印提示，不推送（不会让签到任务失败）。
"""
import json
import os
import urllib.parse
import http.client
import ssl

TIMEOUT = 20
_SSL_CTX = ssl.create_default_context()


def _mask(key):
    if len(key) <= 8:
        return key[:2] + "****"
    return key[:6] + "****" + key[-4:]


def serverchan_url(key):
    """SCT... 用 sctapi.ftqq.com；sctp... 是 Server酱³，要用 https://{uid}.push.ft07.com"""
    if key.lower().startswith("sctp"):
        digits = ""
        for ch in key[4:]:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            return "https://%s.push.ft07.com/send/%s.send" % (digits, key)
    return "https://sctapi.ftqq.com/%s.send" % key


def _post(url, data):
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path + (("?" + parsed.query) if parsed.query else "")
    body = urllib.parse.urlencode(data).encode("utf-8")
    conn = None
    try:
        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443,
                                           timeout=TIMEOUT, context=_SSL_CTX)
        conn.request("POST", path, body=body,
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = conn.getresponse()
        raw = resp.read()
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            return {"code": -1, "msg": raw.decode("utf-8", "replace")[:200]}
    except Exception as exc:  # noqa: BLE001
        return {"code": -1, "msg": "网络请求失败：%s" % exc}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


def main():
    key = (os.environ.get("SERVERCHAN_KEY") or "").strip()
    # 读取上一步的签到日志
    log_text = ""
    for name in ("sign.log",):
        try:
            with open(name, "r", encoding="utf-8", errors="replace") as f:
                log_text = f.read()
        except Exception:  # noqa: BLE001
            pass

    if not log_text:
        log_text = "（未找到签到日志 sign.log）"

    if not key:
        print("[推送] 未配置 SERVERCHAN_KEY，跳过微信推送（在仓库 Settings->Secrets 建一个 SERVERCHAN_KEY 即可）")
        return

    # 简单判断成功/失败，用于标题
    failed = ("失败" in log_text) or ("已失效" in log_text) or ("error" in log_text.lower())
    title = "异环(塔吉多)签到：存在失败项" if failed else "异环(塔吉多)签到：完成"

    body = "```text\n%s\n```" % log_text.strip()
    if len(body) > 4000:
        body = body[:4000] + "\n...（日志过长已截断）"

    url = serverchan_url(key)
    print("[推送] Server酱推送中… key=%s 接口=%s" % (_mask(key), url.split("/")[2]))
    res = _post(url, {"title": title, "desp": body})
    code = res.get("code")
    if code == 0:
        print("[推送] 已推送，请到微信「Server酱Turbo」查看")
    else:
        print("[推送] 推送失败：code=%s msg=%s 原始=%s" % (
            code, res.get("message") or res.get("msg"),
            json.dumps(res, ensure_ascii=False)[:300]))


if __name__ == "__main__":
    main()
