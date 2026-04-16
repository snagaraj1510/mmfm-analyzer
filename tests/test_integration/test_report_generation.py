"""
Report generation integration tests.

Tests that the report command runs without errors and produces valid output.
No real Excel files required — uses the demo inputs already wired into `mmfm report`.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from mmfm.cli import app

runner = CliRunner()


@pytest.fixture
def fake_model_xlsx(tmp_path):
    """Create a minimal Excel file (real parse will fail gracefully, that's fine)."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Revenue Projections"
    ws.append(["year", "stall_rental_income", "vendor_fees", "market_levies", "occupancy_rate"])
    for i, year in enumerate(range(2025, 2030)):
        ws.append([year, 50000 * (1.06 ** i), 10000 * (1.06 ** i), 5000 * (1.05 ** i), 0.70])
    path = tmp_path / "test_model.xlsx"
    wb.save(path)
    return path


class TestReportCommand:
    def test_report_json_with_demo_inputs(self, fake_model_xlsx):
        """mmfm report --format json should produce valid JSON with core metrics."""
        result = runner.invoke(app, ["report", "--file", str(fake_model_xlsx), "--format", "json"])
        # The report command uses demo inputs (_get_demo_inputs) not the Excel file
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "npv" in data
        assert "irr" in data

    def test_report_terminal_does_not_crash(self, fake_model_xlsx):
        """Terminal report should not raise exceptions."""
        result = runner.invoke(app, ["report", "--file", str(fake_model_xlsx), "--format", "terminal"])
        assert result.exit_code == 0

    def test_report_with_scenarios(self, fake_model_xlsx):
        """Report with --scenarios flag should include scenario data."""
        result = runner.invoke(app, [
            "report", "--file", str(fake_model_xlsx),
            "--format", "json", "--scenarios"
        ])
        assert result.exit_code == 0

    def test_report_file_not_found(self, tmp_path):
        """Should exit with code 1 when file does not exist."""
        result = runner.invoke(app, ["report", "--file", str(tmp_path / "missing.xlsx")])
        assert result.exit_code == 1

    def test_report_narrative_mocked(self, fake_model_xlsx):
        """Report with --narrative should call LLM backend (mocked here)."""
        fake_narrative = {
            "executive_summary": "Test narrative.",
            "key_risks": ["collection risk"],
            "recommendation": "proceed",
            "confidence_level": "medium",
            "data_gaps": [],
            "anomalies_flagged": [],
        }
        import json as _json
        mock_backend = MagicMock()
        mock_backend.complete.return_value = _json.dumps(fake_narrative)

        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            result = runner.invoke(app, [
                "report", "--file", str(fake_model_xlsx),
                "--format", "json", "--narrative"
            ])

        assert result.exit_code == 0
        data = _json.loads(result.output)
        assert "narrative" in data
        assert data["narrative"]["recommendation"] == "proceed"
