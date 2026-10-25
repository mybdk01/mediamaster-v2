# -*- coding: utf-8 -*-
"""
统一消息通知模块
支持 Bark（iOS）、钉钉机器人、企业微信机器人、飞书机器人

配置项（存储在数据库 CONFIG 表中）：
    notification              - 总开关 (true/false)
    notification_api_key      - Bark API 密钥
    dingtalk_webhook          - 钉钉机器人 Webhook 地址
    wecom_webhook             - 企业微信机器人 Webhook 地址
    feishu_webhook            - 飞书机器人 Webhook 地址
"""

import json
import logging
import sqlite3
import requests
from datetime import datetime

# 数据库路径（与项目其他脚本一致）
DB_PATH = '/config/data.db'


def load_config(db_path=None):
    """从 SQLite 数据库加载配置"""
    if db_path is None:
        db_path = DB_PATH
    config = {}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT OPTION, VALUE FROM CONFIG")
        for row in cursor.fetchall():
            config[row[0]] = row[1] if row[1] is not None else ""
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
    return config


def _send_bark(api_key, title, body):
    """通过 Bark 发送 iOS 推送"""
    try:
        api_url = f"https://api.day.app/{api_key}"
        data = {"title": title, "body": body}
        headers = {'Content-Type': 'application/json'}
        response = requests.post(api_url, data=json.dumps(data), headers=headers, timeout=10)
        if response.status_code == 200:
            logging.info("Bark 通知发送成功")
            return True
        else:
            logging.error(f"Bark 通知发送失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"Bark 通知发送异常: {e}")
        return False


def _send_dingtalk(webhook, title, body):
    """通过钉钉机器人 Webhook 发送消息"""
    try:
        text = f"【{title}】\n{body}"
        data = {
            "msgtype": "text",
            "text": {"content": text}
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook, data=json.dumps(data), headers=headers, timeout=10)
        result = response.json()
        if response.status_code == 200 and result.get("errcode") == 0:
            logging.info("钉钉通知发送成功")
            return True
        else:
            logging.error(f"钉钉通知发送失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"钉钉通知发送异常: {e}")
        return False


def _send_wecom(webhook, title, body):
    """通过企业微信机器人 Webhook 发送消息"""
    try:
        text = f"【{title}】\n{body}"
        data = {
            "msgtype": "text",
            "text": {"content": text}
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook, data=json.dumps(data), headers=headers, timeout=10)
        result = response.json()
        if response.status_code == 200 and result.get("errcode") == 0:
            logging.info("企业微信通知发送成功")
            return True
        else:
            logging.error(f"企业微信通知发送失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"企业微信通知发送异常: {e}")
        return False


def _send_feishu(webhook, title, body):
    """通过飞书机器人 Webhook 发送消息"""
    try:
        data = {
            "msg_type": "text",
            "content": {"text": f"【{title}】\n{body}"}
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook, data=json.dumps(data), headers=headers, timeout=10)
        result = response.json()
        if response.status_code == 200 and result.get("StatusCode", result.get("code", 0)) == 0:
            logging.info("飞书通知发送成功")
            return True
        else:
            logging.error(f"飞书通知发送失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logging.error(f"飞书通知发送异常: {e}")
        return False


def send_notification(title, body, config=None):
    """
    统一发送通知，自动分发到所有已配置的渠道。

    参数:
        title:   通知标题
        body:    通知正文
        config:  配置字典（可选，不传则自动从数据库加载）
    """
    # 检查总开关
    if config is None:
        config = load_config()

    notification_enabled = config.get("notification", "")
    if notification_enabled.lower() != "true":
        logging.info("通知功能未启用，跳过发送通知。")
        return

    results = []

    # 1. Bark（保留原有功能）
    bark_key = config.get("notification_api_key", "").strip()
    if bark_key:
        results.append(_send_bark(bark_key, title, body))

    # 2. 钉钉
    dingtalk_webhook = config.get("dingtalk_webhook", "").strip()
    if dingtalk_webhook:
        results.append(_send_dingtalk(dingtalk_webhook, title, body))

    # 3. 企业微信
    wecom_webhook = config.get("wecom_webhook", "").strip()
    if wecom_webhook:
        results.append(_send_wecom(wecom_webhook, title, body))

    # 4. 飞书
    feishu_webhook = config.get("feishu_webhook", "").strip()
    if feishu_webhook:
        results.append(_send_feishu(feishu_webhook, title, body))

    if not results:
        logging.warning("未配置任何通知渠道（Bark/钉钉/企微/飞书），无法发送通知。")
    else:
        success_count = sum(1 for r in results if r)
        logging.info(f"通知发送完成: {success_count}/{len(results)} 渠道成功")


# 兼容旧接口：send_notification(title_text) 单参数调用
def send_notification_legacy(title_text, config=None):
    """
    兼容旧代码的单参数调用方式。
    旧代码调用 send_notification(title_text) 时，title_text 实际上是 body 内容。
    """
    if config is None:
        config = load_config()
    send_notification("MediaMaster", title_text, config)
