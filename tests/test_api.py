"""HTTP 层测试：校验 422 行为、正常修复与 NO_REPAIR 响应。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def post(body):
    return client.post("/repair", json=body)


def post_redundant(body):
    return client.post("/repair-redundant", json=body)


class TestOK:
    def test_basic_repair(self):
        r = post({"tokens": [
            {"char": "(", "locked": False},
            {"char": "]", "locked": False},
        ]})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "OK"
        assert data["repaired"] == "()"
        assert data["pairs"] == [[0, 1]]
        assert data["changes"] == [
            {"index": 1, "before": "]", "after": ")"}
        ]

    def test_no_changes(self):
        r = post({"tokens": [
            {"char": "{", "locked": True},
            {"char": "}", "locked": False},
        ]})
        assert r.status_code == 200
        data = r.json()
        assert data["repaired"] == "{}"
        assert data["changes"] == []
        assert data["pairs"] == [[0, 1]]

    def test_locked_kept_cross(self):
        r = post({"tokens": [
            {"char": "(", "locked": True},
            {"char": "[", "locked": False},
            {"char": ")", "locked": False},
            {"char": "]", "locked": True},
        ]})
        data = r.json()
        assert data["status"] == "OK"
        assert data["repaired"] == "()[]"
        # 每个改动位置均可逐位置核验
        assert {c["index"] for c in data["changes"]} == {1, 2}
        for c in data["changes"]:
            i = c["index"]
            src = ["(", "[", ")", "]"][i]
            assert c["before"] == src
        # 锁定位置不在改动列表中
        assert set(c["index"] for c in data["changes"]).isdisjoint({0, 3})

    def test_no_repair_response(self):
        r = post({"tokens": [
            {"char": "(", "locked": True},
            {"char": "(", "locked": True},
        ]})
        assert r.status_code == 200
        data = r.json()
        assert data == {
            "status": "NO_REPAIR",
            "repaired": None,
            "pairs": None,
            "changes": None,
        }

    def test_health(self):
        assert client.get("/health").json() == {"status": "ok"}


class Test422:
    def _expect_422(self, body):
        r = post(body)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]  # FastAPI 标准错误明细

    def test_bad_char(self):
        self._expect_422({"tokens": [
            {"char": "x", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_multi_char_string(self):
        self._expect_422({"tokens": [
            {"char": "()", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_locked_wrong_type_int(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": 1},
            {"char": ")", "locked": 0},
        ]})

    def test_locked_wrong_type_string(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": "true"},
            {"char": ")", "locked": False},
        ]})

    def test_extra_field_in_token(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": False, "id": 1},
            {"char": ")", "locked": False},
        ]})

    def test_extra_field_top_level(self):
        self._expect_422({
            "tokens": [
                {"char": "(", "locked": False},
                {"char": ")", "locked": False},
            ],
            "mode": "force",
        })

    def test_char_wrong_type(self):
        self._expect_422({"tokens": [
            {"char": 1, "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_missing_field(self):
        self._expect_422({"tokens": [
            {"locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_too_short(self):
        self._expect_422({"tokens": [{"char": "(", "locked": False}]})

    def test_odd_length(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": False},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_too_long(self):
        tokens = [{"char": "(", "locked": False}] * 162
        self._expect_422({"tokens": tokens})

    def test_tokens_wrong_type(self):
        self._expect_422({"tokens": "()"})

    def test_empty_tokens(self):
        self._expect_422({"tokens": []})

    def test_null_field(self):
        self._expect_422({"tokens": [
            {"char": None, "locked": False},
            {"char": ")", "locked": False},
        ]})


class TestRedundantOK:
    def test_delete_only(self):
        # 多抄的 "(" 位于原稿下标 0：删除它，零替换
        r = post_redundant({"tokens": [
            {"char": "(", "locked": False},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "OK"
        assert data["repaired"] == "()"
        assert data["deletedIndex"] == 0
        assert data["pairs"] == [[1, 2]]
        assert data["changes"] == []

    def test_delete_middle_and_original_coords(self):
        # 删除中间赘余位后，pairs 与 changes 仍回指原稿坐标
        r = post_redundant({"tokens": [
            {"char": "(", "locked": False},
            {"char": "]", "locked": False},
            {"char": ")", "locked": False},
        ]})
        data = r.json()
        assert data["repaired"] == "()"
        assert data["deletedIndex"] == 1
        assert data["pairs"] == [[0, 2]]
        assert data["changes"] == []

    def test_delete_and_replace(self):
        # "})()("：删下标 4 并把下标 0 的 "}" 改为 "("，共 2 次修改
        r = post_redundant({"tokens": [
            {"char": "}", "locked": False},
            {"char": ")", "locked": False},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
            {"char": "(", "locked": False},
        ]})
        data = r.json()
        assert data["status"] == "OK"
        assert data["repaired"] == "()()"
        assert data["deletedIndex"] == 4
        assert data["pairs"] == [[0, 1], [2, 3]]
        assert data["changes"] == [
            {"index": 0, "before": "}", "after": "("}
        ]

    def test_even_length_matches_repair_endpoint(self):
        body = {"tokens": [
            {"char": "(", "locked": True},
            {"char": "[", "locked": False},
            {"char": ")", "locked": False},
            {"char": "]", "locked": True},
        ]}
        data = post_redundant(body).json()
        assert data["status"] == "OK"
        assert data["deletedIndex"] is None
        # 与 /repair 的偶数长度结果一致
        assert data["repaired"] == post(body).json()["repaired"]
        assert data["pairs"] == [[0, 1], [2, 3]]
        assert data["changes"] == [
            {"index": 1, "before": "[", "after": ")"},
            {"index": 2, "before": ")", "after": "["},
        ]

    def test_no_repair_response(self):
        # 奇数长度全锁定：无可删位
        r = post_redundant({"tokens": [
            {"char": "(", "locked": True},
            {"char": "(", "locked": True},
            {"char": "(", "locked": True},
        ]})
        assert r.status_code == 200
        assert r.json() == {
            "status": "NO_REPAIR",
            "repaired": None,
            "pairs": None,
            "changes": None,
            "deletedIndex": None,
        }

    def test_boundary_lengths_accepted(self):
        # 3 与 81 均为合法长度（/repair 会拒绝奇数，这里必须接受）
        r3 = post_redundant({"tokens": [{"char": "(", "locked": False}] * 3})
        assert r3.status_code == 200
        assert r3.json()["status"] == "OK"
        r81 = post_redundant({"tokens": [{"char": "(", "locked": False}] * 81})
        assert r81.status_code == 200
        assert r81.json()["status"] == "OK"


class TestRedundant422:
    def _expect_422(self, body):
        r = post_redundant(body)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]

    def test_too_short(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_too_long(self):
        self._expect_422({"tokens": [{"char": "(", "locked": False}] * 82})

    def test_empty_tokens(self):
        self._expect_422({"tokens": []})

    def test_bad_char(self):
        self._expect_422({"tokens": [
            {"char": "x", "locked": False},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_locked_wrong_type(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": 1},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})

    def test_extra_field_top_level(self):
        self._expect_422({
            "tokens": [
                {"char": "(", "locked": False},
                {"char": "(", "locked": False},
                {"char": ")", "locked": False},
            ],
            "deletedIndex": 0,
        })

    def test_extra_field_in_token(self):
        self._expect_422({"tokens": [
            {"char": "(", "locked": False, "id": 1},
            {"char": "(", "locked": False},
            {"char": ")", "locked": False},
        ]})
