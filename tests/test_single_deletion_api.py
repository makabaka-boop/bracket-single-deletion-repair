"""单个赘余标记修复入口的 HTTP 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PATH = "/repair-single-deletion"


def post(body):
    return client.post(PATH, json=body)


def tokens(s, locked=None):
    if locked is None:
        locked = [False] * len(s)
    return [
        {"char": ch, "locked": is_locked}
        for ch, is_locked in zip(s, locked)
    ]


class TestSingleDeletionOK:
    def test_delete_redundant_token_with_original_coordinates(self):
        r = post({"tokens": tokens("())")})
        assert r.status_code == 200
        assert r.json() == {
            "status": "OK",
            "repaired": "()",
            # 删除原稿下标 1 后，配对的是原稿 0 与 2。
            "pairs": [[0, 2]],
            "changes": [],
            "deletedIndex": 1,
        }

    def test_delete_without_replacement(self):
        # 删除原稿下标 0 的赘余开括号后，位置 1 与 2 保留为一对 "[]"。
        r = post({"tokens": tokens("[[]")})
        assert r.status_code == 200
        assert r.json() == {
            "status": "OK",
            "repaired": "[]",
            "pairs": [[1, 2]],
            "changes": [],
            "deletedIndex": 0,
        }

    def test_deletion_and_replacement_changes_have_original_indices(self):
        # 删除位置 2，位置 0 '[' 替换为 '('，位置 1 的锁定 ')' 保留。
        r = post({"tokens": tokens("[)]", [False, True, False])})
        assert r.status_code == 200
        assert r.json() == {
            "status": "OK",
            "repaired": "()",
            "pairs": [[0, 1]],
            "changes": [{"index": 0, "before": "[", "after": "("}],
            "deletedIndex": 2,
        }

    def test_even_length_without_deletion_matches_original_repairer(self):
        body = {"tokens": tokens("([)]")}
        old = client.post("/repair", json=body).json()
        new = post(body).json()
        assert new["status"] == "OK"
        assert new["repaired"] == old["repaired"]
        assert new["pairs"] == old["pairs"]
        assert new["changes"] == old["changes"]
        assert new["deletedIndex"] is None

    def test_no_repair_response_shape(self):
        r = post({"tokens": tokens("(((", [True, True, True])})
        assert r.status_code == 200
        assert r.json() == {
            "status": "NO_REPAIR",
            "repaired": None,
            "pairs": None,
            "changes": None,
            "deletedIndex": None,
        }


class TestSingleDeletion422:
    def test_too_short(self):
        assert post({"tokens": tokens("()")}).status_code == 422

    def test_too_long(self):
        body = {"tokens": tokens("(" * 82)}
        assert post(body).status_code == 422

    def test_odd_length_is_accepted_here(self):
        assert post({"tokens": tokens("())")}).status_code == 200

    def test_original_repair_still_rejects_odd_length(self):
        assert client.post("/repair", json={"tokens": tokens("())")}).status_code == 422

    def test_extra_field_is_rejected(self):
        body = {
            "tokens": [
                {"char": "(", "locked": False, "id": 1},
                {"char": ")", "locked": False},
                {"char": ")", "locked": False},
            ]
        }
        assert post(body).status_code == 422

    def test_strict_locked_type(self):
        body = {
            "tokens": [
                {"char": "(", "locked": 1},
                {"char": ")", "locked": False},
                {"char": ")", "locked": False},
            ]
        }
        assert post(body).status_code == 422
