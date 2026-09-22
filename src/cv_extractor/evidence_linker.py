from __future__ import annotations

import re

from ..models.candidate import EvidenceItem
from ..models.taxonomy import SkillTaxonomyItem


class EvidenceLinker:
    """Find exact, boundary-aware textual evidence for extracted skills."""

    @classmethod
    def _extract_bounded_snippet(cls, clean_text: str, match: re.Match, limit: int = 120) -> str:
        """Return a bounded snippet that always includes the exact matched term."""
        if len(clean_text) <= limit:
            return clean_text

        try:
            start_pos = match.start(1)
            end_pos = match.end(1)
        except (IndexError, AttributeError):
            start_pos = match.start()
            end_pos = match.end()

        text_len = len(clean_text)
        match_center = (start_pos + end_pos) // 2
        win_start = max(0, match_center - (limit // 2))
        win_end = min(text_len, win_start + limit)
        if win_end == text_len:
            win_start = max(0, text_len - limit)
        if win_start > start_pos:
            win_start = start_pos
        if win_end < end_pos:
            win_end = end_pos

        snippet_window = clean_text[win_start:win_end]
        prefix = "..." if win_start > 0 else ""
        suffix = "..." if win_end < text_len else ""
        return f"{prefix}{snippet_window}{suffix}"

    @classmethod
    def link_evidence(
        cls,
        skill_name: str,
        taxonomy_item: SkillTaxonomyItem | None,
        sections: dict[str, str],
        full_text: str,
    ) -> list[EvidenceItem]:
        evidence_list: list[EvidenceItem] = []

        keywords = {skill_name.lower()}
        if taxonomy_item:
            keywords.add(taxonomy_item.canonical_name.lower())
            keywords.update(alias.lower() for alias in taxonomy_item.aliases)

        sorted_terms = sorted((term for term in keywords if len(term) >= 2), key=len, reverse=True)
        if not sorted_terms:
            return evidence_list

        terms_regex = "|".join(re.escape(term) for term in sorted_terms)
        pattern = re.compile(rf"(?<!\w)({terms_regex})(?!\w)", re.IGNORECASE)

        # The normalized section key is also the evidence category. This works for both
        # standard and dynamically discovered sections without a second section taxonomy.
        for section, section_text in sections.items():
            snippets = [
                value.strip()
                for value in re.split(r"[\n\r;•\u2022\u25e6|]+", section_text)
                if value.strip()
            ]
            for snippet in snippets:
                clean_snippet = re.sub(r"\s+", " ", snippet).strip()
                match = pattern.search(clean_snippet)
                if not match:
                    continue

                bounded_snippet = cls._extract_bounded_snippet(clean_snippet, match, limit=120)
                if not any(item.text == bounded_snippet for item in evidence_list):
                    evidence_list.append(
                        EvidenceItem(
                            type=section,
                            text=bounded_snippet,
                            source="cv",
                            section=section,
                        )
                    )

        if evidence_list:
            return evidence_list

        for line in (value.strip() for value in full_text.split("\n") if value.strip()):
            clean_line = re.sub(r"\s+", " ", line).strip()
            match = pattern.search(clean_line)
            if match:
                evidence_list.append(
                    EvidenceItem(
                        type="general",
                        text=cls._extract_bounded_snippet(clean_line, match, limit=120),
                        source="cv",
                        section="general",
                    )
                )
                break

        return evidence_list
