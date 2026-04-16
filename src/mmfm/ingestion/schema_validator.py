"""
Schema validation for ingested financial models.

Validates Excel/CSV data against YAML-defined schemas in resources/schemas/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
import pandas as pd

from mmfm.config import SCHEMAS_DIR


@dataclass
class ValidationError:
    sheet: str
    column: str
    row: int | None
    message: str
    severity: Literal["error", "warning"]


@dataclass
class ValidationResult:
    schema_name: str
    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    def add_error(self, sheet: str, column: str, row: int | None, message: str) -> None:
        self.errors.append(ValidationError(sheet, column, row, message, "error"))
        self.passed = False

    def add_warning(self, sheet: str, column: str, row: int | None, message: str) -> None:
        self.warnings.append(ValidationError(sheet, column, row, message, "warning"))

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return (
            f"Schema validation {status}: {self.schema_name} — "
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        )


def load_schema(schema_name: str) -> dict:
    """Load a YAML schema by name from the schemas directory."""
    path = SCHEMAS_DIR / f"{schema_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def _coerce_type(value: Any, expected_type: str) -> tuple[bool, Any]:
    """Try to coerce a value to the expected type. Returns (success, coerced_value)."""
    try:
        if expected_type == "integer":
            return True, int(float(value))
        if expected_type == "float":
            return True, float(value)
        if expected_type == "string":
            return True, str(value)
        return True, value
    except (ValueError, TypeError):
        return False, value


def validate_dataframe(
    df: pd.DataFrame,
    sheet_spec: dict,
    sheet_name: str,
    result: ValidationResult,
) -> None:
    """Validate a single DataFrame against a sheet specification."""
    # Normalize column names: strip whitespace, lowercase for comparison
    df_cols_normalized = {col.strip().lower(): col for col in df.columns}

    for col_spec in sheet_spec.get("required_columns", []):
        col_name = col_spec["name"]
        col_name_lower = col_name.lower()

        if col_name_lower not in df_cols_normalized:
            result.add_error(sheet_name, col_name, None, f"Required column '{col_name}' not found")
            continue

        actual_col = df_cols_normalized[col_name_lower]
        col_data = df[actual_col].dropna()

        for idx, value in col_data.items():
            expected_type = col_spec.get("type", "string")
            success, coerced = _coerce_type(value, expected_type)
            if not success:
                result.add_error(
                    sheet_name, col_name, int(idx),
                    f"Cannot coerce '{value}' to {expected_type}"
                )
                continue

            if "min" in col_spec and coerced < col_spec["min"]:
                result.add_warning(
                    sheet_name, col_name, int(idx),
                    f"Value {coerced} is below minimum {col_spec['min']}"
                )
            if "max" in col_spec and coerced > col_spec["max"]:
                result.add_warning(
                    sheet_name, col_name, int(idx),
                    f"Value {coerced} exceeds maximum {col_spec['max']}"
                )
            if "allowed_values" in col_spec and str(coerced) not in col_spec["allowed_values"]:
                result.add_error(
                    sheet_name, col_name, int(idx),
                    f"Value '{coerced}' not in allowed values: {col_spec['allowed_values']}"
                )

    for col_spec in sheet_spec.get("optional_columns", []):
        col_name = col_spec["name"]
        col_name_lower = col_name.lower()
        if col_name_lower in df_cols_normalized:
            actual_col = df_cols_normalized[col_name_lower]
            col_data = df[actual_col].dropna()
            for idx, value in col_data.items():
                expected_type = col_spec.get("type", "string")
                success, coerced = _coerce_type(value, expected_type)
                if not success:
                    result.add_warning(
                        sheet_name, col_name, int(idx),
                        f"Cannot coerce optional column '{value}' to {expected_type}"
                    )


def validate_lead_time_rules(
    df: pd.DataFrame,
    schema: dict,
    sheet_name: str,
    result: ValidationResult,
) -> None:
    """
    Validate lead-time rules from the schema's lead_time_rules section.

    For each rule, finds rows where the item name matches the pattern
    and checks that lead_time_months >= min_lead_time_months.
    """
    lead_time_rules = schema.get("lead_time_rules", [])
    if not lead_time_rules:
        return

    # Normalize column names
    cols_lower = {col.strip().lower(): col for col in df.columns}
    item_col = cols_lower.get("item")
    lead_col = cols_lower.get("lead_time_months")

    if item_col is None or lead_col is None:
        # Can't validate without both columns
        return

    for rule in lead_time_rules:
        pattern = rule.get("item_pattern", "").lower()
        min_months = rule.get("min_lead_time_months", 0)
        warning_msg = rule.get("warning_message", f"Lead time below minimum for '{pattern}' items")

        for idx, row in df.iterrows():
            item_val = str(row[item_col]).lower() if pd.notna(row[item_col]) else ""
            lead_val = row[lead_col]

            if pattern in item_val and pd.notna(lead_val):
                try:
                    lead_months = int(float(lead_val))
                    if lead_months < min_months:
                        result.add_warning(
                            sheet_name,
                            "lead_time_months",
                            int(idx),
                            f"{warning_msg} (got {lead_months}, min {min_months})",
                        )
                except (ValueError, TypeError):
                    pass


def validate_sheets(
    sheets: dict[str, pd.DataFrame],
    schema: dict,
) -> ValidationResult:
    """
    Validate a dict of {sheet_name: DataFrame} against a loaded schema.

    Args:
        sheets: Dict mapping sheet name -> DataFrame
        schema: Loaded YAML schema dict

    Returns:
        ValidationResult with all errors and warnings
    """
    result = ValidationResult(schema_name=schema.get("name", "unknown"), passed=True)

    # Normalize sheet names for comparison
    sheets_normalized = {name.strip().lower(): name for name in sheets}

    for sheet_spec in schema.get("required_sheets", []):
        expected_name = sheet_spec["name"]
        expected_lower = expected_name.lower()

        if expected_lower not in sheets_normalized:
            result.add_error(expected_name, "", None, f"Required sheet '{expected_name}' not found")
            continue

        actual_name = sheets_normalized[expected_lower]
        df = sheets[actual_name]
        validate_dataframe(df, sheet_spec, expected_name, result)

        # Apply lead-time rules if present in schema
        if schema.get("lead_time_rules"):
            validate_lead_time_rules(df, schema, expected_name, result)

    return result
