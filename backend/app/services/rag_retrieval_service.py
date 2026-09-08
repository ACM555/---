from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.models.assistant import AssistantPassage, AssistantSource
from app.services.assistant_knowledge import KnowledgeDocument, SYSTEM_GUIDES
from app.models.legal import LegalSourceSearch
from app.services.legal_repository import LegalRepository


@dataclass(frozen=True)
class RetrievedKnowledge:
    source: AssistantSource
    content: str


def _tokens(value: str) -> set[str]:
    latin = re.findall(r"[a-z0-9_]{2,}", value.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", value)
    return set(latin + chinese)


def _excerpt(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:240] + ("…" if len(compact) > 240 else "")


class RetrievalService:
    """Tenant-scoped lexical retrieval with a seam for future embeddings."""

    def __init__(self) -> None:
        self._legal_repository = LegalRepository()

    def retrieve(self, question: str, user_id: str, limit: int = 5) -> list[RetrievedKnowledge]:
        legal_documents = self._legal_documents(question, limit)
        if legal_documents:
            return legal_documents
        documents = [*SYSTEM_GUIDES, *self._tenant_documents(user_id)]
        query_tokens = _tokens(question)
        ranked: list[tuple[int, KnowledgeDocument]] = []
        for document in documents:
            score = len(query_tokens & _tokens(f"{document.title} {document.content}"))
            if score:
                ranked.append((score, document))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[:limit] or [(0, SYSTEM_GUIDES[0])]
        return [
            RetrievedKnowledge(
                source=AssistantSource(
                    id=document.id,
                    title=document.title,
                    excerpt=_excerpt(document.content),
                ),
                content=document.content,
            )
            for _, document in selected
        ]

    def retrieve_legal(self, question: str, limit: int = 5) -> list[RetrievedKnowledge]:
        return self._legal_documents(question, limit)

    def _legal_documents(self, question: str, limit: int) -> list[RetrievedKnowledge]:
        country_code = self._detect_country(question)
        if country_code is None:
            return []
        legal_module = self._detect_module(question)
        # Country alone is not a sufficient legal retrieval condition: an
        # unclassified question must not receive materials from another module.
        if legal_module is None:
            return []
        sources = self._legal_repository.search_sources(
            LegalSourceSearch(
                country_code=country_code,
                legal_module=legal_module,
                limit=limit,
            )
        )
        return [
            RetrievedKnowledge(
                source=AssistantSource(
                    id=source.source_id,
                    title=source.title,
                    excerpt=_excerpt(source.supported_fact),
                    source_url=str(source.source_url),
                    country_code=source.country_code,
                    legal_module=source.legal_module,
                    evidence_level=source.evidence_level,
                    source_type=source.source_type,
                    source_language=source.source_language,
                    verified_at=source.verified_at.isoformat(),
                    effective_at=source.effective_at.isoformat() if source.effective_at else None,
                    prerequisites=source.prerequisites,
                    non_inferences=source.non_inferences,
                    review_triggers=source.review_triggers,
                    passages=[
                        AssistantPassage(
                            locator=passage.locator,
                            original_text=passage.original_text,
                            chinese_text=passage.chinese_text,
                            effective_at=passage.effective_at.isoformat() if passage.effective_at else None,
                        )
                        for passage in self._legal_repository.list_passages(source.source_id, "approved")
                    ],
                ),
                content=(
                    f"资料等级：{source.evidence_level}\n"
                    f"可支持的有限事实：{source.supported_fact}\n"
                    f"适用前提：{'；'.join(source.prerequisites)}\n"
                    f"不能推断：{'；'.join(source.non_inferences)}\n"
                    f"需人工复核：{'；'.join(source.review_triggers)}\n"
                    f"原文链接：{source.source_url}"
                ),
            )
            for source in sources
            # A source without an approved, traceable clause excerpt is not
            # evidence for a user-facing legal answer.
            if self._legal_repository.list_passages(source.source_id, "approved")
        ]

    @staticmethod
    def _detect_country(question: str) -> str | None:
        normalized = question.lower()
        aliases = {
            "BN": ("文莱", "brunei"),
            "KH": ("柬埔寨", "cambodia"),
            "ID": ("印尼", "印度尼西亚", "indonesia"),
            "LA": ("老挝", "laos"),
            "MY": ("马来西亚", "malaysia"),
            "MM": ("缅甸", "myanmar"),
            "PH": ("菲律宾", "philippines"),
            "SG": ("新加坡", "singapore"),
            "TH": ("泰国", "thailand"),
            "TL": ("东帝汶", "timor-leste", "timor leste"),
            "VN": ("越南", "vietnam"),
        }
        matches = [
            country_code
            for country_code, country_aliases in aliases.items()
            if any(alias in question or alias in normalized for alias in country_aliases)
        ]
        # A single retrieval must never silently apply one country's materials to
        # a multi-country question. The orchestrator turns an empty result into
        # an explicit "需人工复核" response.
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _detect_module(question: str) -> str | None:
        if any(keyword in question for keyword in ("投资", "设立", "公司", "准入", "持股", "承接工程")):
            return "M1"
        if any(keyword in question for keyword in ("合同", "违约", "条款", "分销", "买卖协议")):
            return "M2"
        if any(keyword in question for keyword in ("运输", "贸易", "出口", "进口", "报关", "Incoterms")):
            return "M3"
        if any(keyword in question for keyword in ("工作许可", "签证", "派驻", "劳动", "雇员", "员工")):
            return "M4"
        if any(keyword in question for keyword in ("商标", "专利", "著作权", "知识产权", "技术保护", "PCT")):
            return "M5"
        if any(keyword in question for keyword in ("仲裁", "争议", "货款", "追偿", "执行", "判决", "裁决")):
            return "M6"
        return None

    def store_text_document(self, user_id: str, filename: str, content: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename) or "document.txt"
        directory = Path(settings.ASSISTANT_KNOWLEDGE_DIR) / user_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / safe_name).write_text(content, encoding="utf-8")
        return f"tenant-{user_id}-{safe_name}"

    def _tenant_documents(self, user_id: str) -> list[KnowledgeDocument]:
        directory = Path(settings.ASSISTANT_KNOWLEDGE_DIR) / user_id
        if not directory.exists():
            return []
        documents: list[KnowledgeDocument] = []
        for path in directory.glob("*.txt"):
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if content.strip():
                documents.append(
                    KnowledgeDocument(
                        id=f"tenant-{user_id}-{path.name}",
                        title=f"用户资料：{path.name}",
                        content=content[:20_000],
                    )
                )
        return documents
