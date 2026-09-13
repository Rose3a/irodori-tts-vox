"""Persistent pronunciation overrides and Japanese speech preprocessing."""
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import unicodedata
import uuid

import alkana

LETTER_KANA = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", (
    "エー", "ビー", "シー", "ディー", "イー", "エフ", "ジー", "エイチ",
    "アイ", "ジェイ", "ケー", "エル", "エム", "エヌ", "オー", "ピー",
    "キュー", "アール", "エス", "ティー", "ユー", "ブイ", "ダブリュー",
    "エックス", "ワイ", "ゼット",
)))

# Common Japanese readings used in the Irodori/VOICEVOX tooling ecosystem.
# User dictionary entries are applied after these defaults and can override them.
BUILTIN_READINGS = {
    "irodori": "いろどり", "voicevox": "ボイスボックス", "github": "ギットハブ",
    "git": "ギット", "gradio": "グラディオ", "python": "パイソン",
    "javascript": "ジャバスクリプト", "typescript": "タイプスクリプト",
    "nodejs": "ノードジェイエス", "node.js": "ノードジェイエス",
    "npm": "エヌピーエム", "pnpm": "ピーニーピーエム", "api": "エーピーアイ",
    "ui": "ユーアイ", "gui": "グイ", "cli": "シーエルアイ",
    "tts": "ティーティーエス", "asr": "エーエスアール", "ai": "エーアイ",
    "openai": "オープンエーアイ", "chatgpt": "チャットジーピーティー",
    "huggingface": "ハギングフェイス", "pytorch": "パイトーチ",
    "cuda": "クーダ", "onnx": "オーエヌエヌエックス", "directml": "ダイレクトエムエル",
    "tensorRT": "テンソルアールティー", "docker": "ドッカー", "windows": "ウィンドウズ",
    "browser": "ブラウザー", "chrome": "クローム", "edge": "エッジ",
    "download": "ダウンロード", "upload": "アップロード", "online": "オンライン",
    "offline": "オフライン", "login": "ログイン", "logout": "ログアウト",
    "streaming": "ストリーミング", "software": "ソフトウェア", "hardware": "ハードウェア",
    "server": "サーバー", "client": "クライアント", "cache": "キャッシュ",
    "model": "モデル", "prompt": "プロンプト", "token": "トークン",
}


def normalize_width(text):
    # Keep Japanese punctuation and full-width kana intact.
    return text.translate({**{i: i - 0xFEE0 for i in range(0xFF01, 0xFF5F)}, 0x3000: 0x20})


def make_word(surface, pronunciation, accent_type=0, priority=5):
    if not isinstance(surface, str) or not surface.strip():
        raise ValueError("単語は必須です")
    if not isinstance(pronunciation, str):
        raise ValueError("読みはカタカナで入力してください")
    pronunciation = unicodedata.normalize("NFKC", pronunciation)
    pronunciation = ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in pronunciation)
    if not re.fullmatch(r"[ァ-ヴー]+", pronunciation):
        raise ValueError("読みはひらがな・カタカナで入力してください")
    count = len(re.findall(r"[ァ-ヴー][ァィゥェォャュョヮ]?", pronunciation))
    accent_type, priority = int(accent_type), int(priority)
    if not 0 <= priority <= 10 or not 0 <= accent_type <= count:
        raise ValueError("優先度またはアクセントの範囲が不正です")
    return dict(surface=normalize_width(surface), pronunciation=pronunciation,
                yomi=pronunciation, accent_type=accent_type, priority=priority,
                mora_count=count, part_of_speech="名詞", part_of_speech_detail_1="固有名詞",
                part_of_speech_detail_2="一般", part_of_speech_detail_3="*",
                inflectional_type="*", inflectional_form="*", stem="*",
                accent_associative_rule="*")


class ReadingDictionary:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.words = {}
        if self.path.exists():
            self.words = self._validate(json.loads(self.path.read_text(encoding="utf-8")))

    @staticmethod
    def _validate(words):
        if not isinstance(words, dict):
            raise ValueError("辞書はオブジェクトで指定してください")
        result = {}
        for key, word in words.items():
            uuid.UUID(key)
            if not isinstance(word, dict):
                raise ValueError("辞書の単語が不正です")
            result[key] = make_word(word.get("surface"), word.get("pronunciation"),
                                    word.get("accent_type", 0), word.get("priority", 5))
        return result

    def snapshot(self):
        with self.lock:
            return {key: dict(value) for key, value in self.words.items()}

    def _save(self, words):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(words, stream, ensure_ascii=False, indent=2)
            os.replace(name, self.path)
            self.words = words
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def put(self, word, key=None):
        with self.lock:
            if key is not None and key not in self.words:
                raise KeyError("単語が見つかりません")
            key = key or str(uuid.uuid4())
            self._save({**self.words, **self._validate({key: word})})
            return key

    def delete(self, key):
        with self.lock:
            words = self.snapshot()
            del words[key]
            self._save(words)

    def import_words(self, words, override):
        incoming = self._validate(words)
        with self.lock:
            self._save({**self.words, **incoming} if override else {**incoming, **self.words})

    def convert(self, text):
        text = normalize_width(text)
        words = sorted(self.snapshot().values(),
                       key=lambda w: (-len(w["surface"]), -w["priority"]))
        readings = {normalize_width(key).lower(): value for key, value in BUILTIN_READINGS.items()}
        user_surfaces = set()
        for word in words:
            surface = normalize_width(word["surface"]).lower()
            # If the same surface is registered more than once, keep the
            # highest-priority pronunciation (the list is already priority-sorted).
            if surface not in user_surfaces:
                readings[surface] = word["pronunciation"]
                user_surfaces.add(surface)
        # One pass: replacements are never passed through the dictionary again.
        def english(value):
            def convert(match):
                token = match[0]
                # Initialisms and one-letter words are pronounced letter by letter.
                if len(token) == 1 or (token.isupper() and len(token) > 1):
                    return ''.join(LETTER_KANA[c.upper()] for c in token)
                return alkana.get_kana(token.lower()) or token
            return re.sub(r"[A-Za-z]+(?:['’][A-Za-z]+)?", convert, value)
        if not readings:
            return english(text)
        pattern = re.compile('|'.join(re.escape(k) for k in readings), re.IGNORECASE | re.ASCII)
        result, start = [], 0
        for match in pattern.finditer(text):
            result.extend((english(text[start:match.start()]), readings[match[0].lower()]))
            start = match.end()
        return ''.join(result) + english(text[start:])


READING_DICTIONARY = ReadingDictionary(Path(__file__).resolve().parents[2] / "user_dictionary.json")
