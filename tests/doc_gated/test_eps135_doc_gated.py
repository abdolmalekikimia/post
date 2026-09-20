"""E2E doc-gated tests for EPS-135: Barcode / Label / Center-Code Replacement.

These tests are gated by the ``RUN_EPS135=1`` environment variable because they
depend on receiving official R1 documentation and are validated against the Edge
application after patch deployment.

Run locally (will skip):
    pytest tests/doc_gated/test_eps135_doc_gated.py -v

Run with gating enabled:
    $env:RUN_EPS135="1"
    pytest tests/doc_gated/test_eps135_doc_gated.py -v
"""

from __future__ import annotations

import os

import pytest

from flows.edge_doc_gated.eps135_doc_gate_flow import (
    run_eps135_flow,
    run_tc01_barcodes,
    run_tc02_labels,
    run_tc03_centers,
    run_tc04_verify,
    run_tc05_doc_gate,
)


# ---------------------------------------------------------------------------
# Environment gating
# ---------------------------------------------------------------------------

_EPS135_ENABLED = os.getenv("RUN_EPS135", "0").lower() in {"1", "true", "yes", "on"}


def _skip_unless_enabled() -> None:
    if not _EPS135_ENABLED:
        pytest.skip(
            "EPS-135 doc-gated tests require $env:RUN_EPS135=1 "
            "and receipt of R1 documentation"
        )


# ---------------------------------------------------------------------------
# Integration tests — all skipped until R1 docs arrive
# ---------------------------------------------------------------------------


@pytest.mark.doc_gated
@pytest.mark.eps135
class TestEps135DocGated:
    """Doc-gated integration tests for official value replacement."""

    def test_tc01_barcode_replacement_on_edge(self):
        """TC-01: Deploy official barcodes and verify via Edge application."""
        _skip_unless_enabled()
        result = run_tc01_barcodes(slot=10)
        # After R1 arrival: verify against Edge API endpoint
        assert len(result.report.records) >= 4

    def test_tc02_label_replacement_on_edge(self):
        """TC-02: Deploy official label spec and verify via bag.close response."""
        _skip_unless_enabled()
        result = run_tc02_labels(slot=10)
        assert result.summary["official_barcode"].startswith("60")

    def test_tc03_center_codes_replacement_on_edge(self):
        """TC-03: Deploy official center codes and verify via Edge config."""
        _skip_unless_enabled()
        result = run_tc03_centers()
        assert result.summary["official_count"] >= 3

    def test_tc04_full_validation_on_edge(self):
        """TC-04: Run full validation suite after all replacements applied."""
        _skip_unless_enabled()
        result = run_tc04_verify(slot=10)
        assert len(result.summary["barcodes"]) >= 1

    def test_tc05_doc_gate_still_open(self):
        """TC-05: Verify story remains open while R1 documents are pending."""
        _skip_unless_enabled()
        result = run_tc05_doc_gate(all_docs_received=False)
        assert result.summary["all_docs_received"] is False

    def test_unified_flow_all_five_scenarios(self):
        """Run all five scenarios as a complete doc-gated validation."""
        _skip_unless_enabled()
        results = run_eps135_flow(slot=20, all_docs_received=False)
        assert len(results) == 5
        for r in results:
            assert r.case.case_id in {"TC-01", "TC-02", "TC-03", "TC-04", "TC-05"}
