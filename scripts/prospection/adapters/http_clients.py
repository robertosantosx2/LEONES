#!/usr/bin/env python3
"""Small dependency-free HTTP helpers for public discovery endpoints.

Authentication, pagination and rate-limit policy remain caller concerns.
Every response is returned with its request URL so provenance can be retained.
"""
from __future__ import annotations
import json
from urllib.request import Request,urlopen


def get_json(url: str, *, headers: dict[str,str]|None=None, timeout: int=20):
    h={"User-Agent":"LEONES-Atlas-Prospection/1.0","Accept":"application/json"}
    if headers: h.update(headers)
    req=Request(url,headers=h,method="GET")
    with urlopen(req,timeout=timeout) as r:
        return {"url":url,"status":r.status,"data":json.loads(r.read().decode("utf-8"))}
