from pathlib import Path
import json
from collections import Counter, defaultdict

import pandas as pd

from src.utils.normalization import build_key


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_csv"
REPORTS_DIR = DATA_DIR / "reports"

EQUIVALENCY_FILE = DATA_DIR / "paint_equivalency_database.csv"

OUTPUT_JSON = REPORTS_DIR / "enrichment_diagnostic_summary.json"
OUTPUT_CSV = REPORTS_DIR / "enrichment_diagnostic.csv"
OUTPUT_MD = REPORTS_DIR / "enrichment_analysis.md"

SUPPORTED_COMPANIES = {
    build_key("Army Painter"),
    build_key("Games Workshop"),
    build_key("Citadel"),
    build_key("Vallejo"),
    build_key("AK Interactive"),
    build_key("Pro Acryl"),
    build_key("Monument"),
}

REGISTRY_COLUMNS = [
    "Paint_ID",
    "Company",
    "Brand",
    "Product_Line",
    "Paint_Name",
    "Hex",
    "RGB",
    "Paint_Type",
    "Status",
    "Source",
    "Notes",
]


def is_blank(value) -> bool:
    if pd.isna(value):
        return True
    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def has_color_data(row) -> bool:
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def similarity_to_number(value) -> float:
    value = str(value).replace("%", "").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


def load_registries():
    registry_rows = []
    exact_lookup = defaultdict(list)
    loose_lookup = defaultdict(list)

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        for column in REGISTRY_COLUMNS:
            if column not in df.columns:
                df[column] = ""

        for _, row in df.iterrows():
            record = {
                "Registry_File": file_path.name,
                "Paint_ID": row.get("Paint_ID", ""),
                "Company": row.get("Company", ""),
                "Brand": row.get("Brand", ""),
                "Product_Line": row.get("Product_Line", ""),
                "Paint_Name": row.get("Paint_Name", ""),
                "Hex": row.get("Hex", ""),
                "RGB": row.get("RGB", ""),
                "Paint_Type": row.get("Paint_Type", ""),
                "Status": row.get("Status", ""),
                "Source": row.get("Source", ""),
                "Notes": row.get("Notes", ""),
            }

            registry_rows.append(record)

            exact_lookup[
                build_key(record["Company"], record["Product_Line"], record["Paint_Name"])
            ].append(record)

            loose_lookup[
                build_key(record["Company"], record["Paint_Name"])
            ].append(record)

    return registry_rows, exact_lookup, loose_lookup


def prepare_equivalencies():
    if not EQUIVALENCY_FILE.exists():
        raise FileNotFoundError(f"Missing equivalency file: {EQUIVALENCY_FILE}")

    df = pd.read_csv(EQUIVALENCY_FILE)

    needed_columns = [
        "Source_Company",
        "Source_Product_Line",
        "Source_Paint_Name",
        "Equivalent_Company",
        "Equivalent_Product_Line",
        "Equivalent_Paint_Name",
        "Similarity_Percent",
        "Confidence",
        "Match_Type",
        "Source",
        "Notes",
    ]

    for column in needed_columns:
        if column not in df.columns:
            df[column] = ""

    df["_source_exact_key"] = df.apply(
        lambda row: build_key(
            row.get("Source_Company"),
            row.get("Source_Product_Line"),
            row.get("Source_Paint_Name"),
        ),
        axis=1,
    )

    df["_source_loose_key"] = df.apply(
        lambda row: build_key(
            row.get("Source_Company"),
            row.get("Source_Paint_Name"),
        ),
        axis=1,
    )

    df["_equivalent_exact_key"] = df.apply(
        lambda row: build_key(
            row.get("Equivalent_Company"),
            row.get("Equivalent_Product_Line"),
            row.get("Equivalent_Paint_Name"),
        ),
        axis=1,
    )

    df["_equivalent_loose_key"] = df.apply(
        lambda row: build_key(
            row.get("Equivalent_Company"),
            row.get("Equivalent_Paint_Name"),
        ),
        axis=1,
    )

    df["_similarity_number"] = df["Similarity_Percent"].apply(similarity_to_number)

    return df


def find_same_company_candidates(missing, registry_rows):
    candidates = []

    missing_company_key = build_key(missing.get("Company"))
    missing_name_key = build_key(missing.get("Paint_Name"))
    missing_id = str(missing.get("Paint_ID", "")).strip()

    for row in registry_rows:
        row_id = str(row.get("Paint_ID", "")).strip()

        if row_id and missing_id and row_id == missing_id:
            continue

        if build_key(row.get("Company")) != missing_company_key:
            continue

        if build_key(row.get("Paint_Name")) != missing_name_key:
            continue

        candidates.append(row)

    return candidates


def find_equivalency_candidates(missing, equivalencies):
    exact_key = build_key(
        missing.get("Company"),
        missing.get("Product_Line"),
        missing.get("Paint_Name"),
    )

    loose_key = build_key(
        missing.get("Company"),
        missing.get("Paint_Name"),
    )

    matches = equivalencies[equivalencies["_source_exact_key"] == exact_key]

    if matches.empty:
        matches = equivalencies[equivalencies["_source_loose_key"] == loose_key]

    return matches.sort_values("_similarity_number", ascending=False)


def find_registry_matches_for_equivalent(equiv, exact_lookup, loose_lookup):
    exact_key = equiv.get("_equivalent_exact_key")
    loose_key = equiv.get("_equivalent_loose_key")

    matches = exact_lookup.get(exact_key, [])

    if matches:
        return matches

    return loose_lookup.get(loose_key, [])


def make_report_row(
    missing,
    diagnosis,
    status,
    action,
    candidate=None,
    equiv=None,
    reason_detail="",
):
    if candidate is None:
        candidate = {}

    if equiv is None:
        equiv = {}

    if hasattr(equiv, "to_dict"):
        equiv = equiv.to_dict()

    if hasattr(candidate, "to_dict"):
        candidate = candidate.to_dict()

    return {
        "Status": status,
        "Diagnosis": diagnosis,
        "Recommended_Action": action,
        "Reason_Detail": reason_detail,

        "Missing_Registry_File": missing.get("Registry_File", ""),
        "Missing_Paint_ID": missing.get("Paint_ID", ""),
        "Missing_Company": missing.get("Company", ""),
        "Missing_Brand": missing.get("Brand", ""),
        "Missing_Product_Line": missing.get("Product_Line", ""),
        "Missing_Paint_Name": missing.get("Paint_Name", ""),
        "Missing_Paint_Type": missing.get("Paint_Type", ""),
        "Missing_Status": missing.get("Status", ""),
        "Missing_Hex": missing.get("Hex", ""),
        "Missing_RGB": missing.get("RGB", ""),

        "Candidate_Paint_ID": candidate.get("Paint_ID", ""),
        "Candidate_Company": candidate.get("Company", equiv.get("Equivalent_Company", "")),
        "Candidate_Brand": candidate.get("Brand", ""),
        "Candidate_Product_Line": candidate.get("Product_Line", equiv.get("Equivalent_Product_Line", "")),
        "Candidate_Paint_Name": candidate.get("Paint_Name", equiv.get("Equivalent_Paint_Name", "")),
        "Candidate_Paint_Type": candidate.get("Paint_Type", ""),
        "Candidate_Hex": candidate.get("Hex", ""),
        "Candidate_RGB": candidate.get("RGB", ""),

        "Equivalent_Source_Company": equiv.get("Source_Company", ""),
        "Equivalent_Source_Product_Line": equiv.get("Source_Product_Line", ""),
        "Equivalent_Source_Paint_Name": equiv.get("Source_Paint_Name", ""),
        "Equivalent_Target_Company": equiv.get("Equivalent_Company", ""),
        "Equivalent_Target_Product_Line": equiv.get("Equivalent_Product_Line", ""),
        "Equivalent_Target_Paint_Name": equiv.get("Equivalent_Paint_Name", ""),
        "Similarity_Percent": equiv.get("Similarity_Percent", ""),
        "Confidence": equiv.get("Confidence", ""),
        "Match_Type": equiv.get("Match_Type", ""),
        "Reference_Source": equiv.get("Source", ""),
        "Reference_Notes": equiv.get("Notes", ""),
    }


def diagnose_missing_row(missing, registry_rows, equivalencies, exact_lookup, loose_lookup):
    same_company_candidates = find_same_company_candidates(missing, registry_rows)

    same_company_with_color = [
        row for row in same_company_candidates
        if has_color_data(row)
    ]

    if same_company_with_color:
        candidate = same_company_with_color[0]

        return make_report_row(
            missing=missing,
            diagnosis="Same-company paint name match has usable Hex/RGB",
            status="AUTO_FILL_SAME_COMPANY",
            action="Auto fill Hex/RGB from same company paint with matching name.",
            candidate=candidate,
            reason_detail=(
                f"Found same company and paint name in product line "
                f"{candidate.get('Product_Line')} with Hex/RGB."
            ),
        )

    equivalency_candidates = find_equivalency_candidates(missing, equivalencies)

    if equivalency_candidates.empty:
        if same_company_candidates:
            return make_report_row(
                missing=missing,
                diagnosis="Same-company paint name exists but lacks usable Hex/RGB",
                status="SAME_COMPANY_MATCH_MISSING_COLOR",
                action="Manual review or enrich one of the matching same-company rows first.",
                candidate=same_company_candidates[0],
                reason_detail="Same-company paint name exists, but no matching row has both Hex and RGB.",
            )

        return make_report_row(
            missing=missing,
            diagnosis="No same-company or equivalency match found",
            status="MANUAL_RESEARCH",
            action="Manual research required.",
            reason_detail="No matching same-company paint name and no equivalency source match found.",
        )

    unsupported_equivs = []
    target_missing_color = []

    for _, equiv in equivalency_candidates.iterrows():
        target_company_key = build_key(equiv.get("Equivalent_Company"))

        if target_company_key not in SUPPORTED_COMPANIES:
            unsupported_equivs.append(equiv)
            continue

        registry_matches = find_registry_matches_for_equivalent(
            equiv,
            exact_lookup,
            loose_lookup,
        )

        if not registry_matches:
            continue

        color_matches = [
            row for row in registry_matches
            if has_color_data(row)
        ]

        if color_matches:
            return make_report_row(
                missing=missing,
                diagnosis="Equivalency match has usable Hex/RGB",
                status="AUTO_FILL_EQUIVALENCY",
                action="Auto fill Hex/RGB from best available equivalency match.",
                candidate=color_matches[0],
                equiv=equiv,
                reason_detail="Equivalency target exists in supported registries and has Hex/RGB.",
            )

        target_missing_color.append((equiv, registry_matches[0]))

    if target_missing_color:
        equiv, candidate = target_missing_color[0]

        return make_report_row(
            missing=missing,
            diagnosis="Equivalency target exists but lacks usable Hex/RGB",
            status="EQUIVALENCY_TARGET_MISSING_COLOR",
            action="Enrich the target paint first, then rerun this audit.",
            candidate=candidate,
            equiv=equiv,
            reason_detail="Equivalent paint exists in registry but does not have both Hex and RGB.",
        )

    if unsupported_equivs:
        equiv = unsupported_equivs[0]

        return make_report_row(
            missing=missing,
            diagnosis="Equivalency only points to unsupported company",
            status="UNSUPPORTED_EQUIVALENCY_COMPANY",
            action="Ignore for automatic enrichment unless this manufacturer is added later.",
            equiv=equiv,
            reason_detail="Equivalency exists, but target company is not part of the current registry set.",
        )

    best_equiv = equivalency_candidates.iloc[0]

    return make_report_row(
        missing=missing,
        diagnosis="Equivalency exists but target paint was not found in registries",
        status="EQUIVALENCY_TARGET_NOT_IN_REGISTRY",
        action="Check naming/product-line mismatch or add target paint to registry.",
        equiv=best_equiv,
        reason_detail="Equivalency match exists, but no matching target paint was found in loaded registries.",
    )


def build_markdown_report(summary, status_counts, company_counts, product_line_counts):
    lines = []

    lines.append("# Enrichment Diagnostic Analysis")
    lines.append("")
    lines.append("## Overall Summary")
    lines.append("")
    lines.append(f"- Registries checked: {summary['registries_checked']}")
    lines.append(f"- Total registry rows: {summary['total_registry_rows']}")
    lines.append(f"- Missing Hex/RGB rows checked: {summary['missing_rows_checked']}")
    lines.append(f"- Auto-fill same company: {summary['auto_fill_same_company']}")
    lines.append(f"- Auto-fill equivalency: {summary['auto_fill_equivalency']}")
    lines.append(f"- Needs review/manual work: {summary['needs_review_or_manual']}")
    lines.append("")

    lines.append("## Status Breakdown")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|---|---:|")

    for status, count in status_counts.items():
        lines.append(f"| {status} | {count} |")

    lines.append("")
    lines.append("## Missing Rows by Company")
    lines.append("")
    lines.append("| Company | Count |")
    lines.append("|---|---:|")

    for company, count in company_counts.items():
        lines.append(f"| {company} | {count} |")

    lines.append("")
    lines.append("## Missing Rows by Product Line")
    lines.append("")
    lines.append("| Product Line | Count |")
    lines.append("|---|---:|")

    for product_line, count in product_line_counts.items():
        lines.append(f"| {product_line} | {count} |")

    lines.append("")
    lines.append("## Recommended Workflow")
    lines.append("")
    lines.append("1. Review `AUTO_FILL_SAME_COMPANY` rows first.")
    lines.append("2. Review `AUTO_FILL_EQUIVALENCY` rows second.")
    lines.append("3. Investigate `EQUIVALENCY_TARGET_MISSING_COLOR` rows because enriching those targets may unlock more rows.")
    lines.append("4. Ignore or defer unsupported companies unless you add those manufacturers later.")
    lines.append("5. Manually research remaining `MANUAL_RESEARCH` rows.")
    lines.append("")

    return "\n".join(lines)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    registry_rows, exact_lookup, loose_lookup = load_registries()
    equivalencies = prepare_equivalencies()

    missing_rows = [
        row for row in registry_rows
        if is_blank(row.get("Hex")) or is_blank(row.get("RGB"))
    ]
    print("\nFIRST MISSING ROW")
    print("-----------------")
    print(missing_rows[0])
    print(type(missing_rows[0]))

    report_rows = [
        diagnose_missing_row(
            missing=row,
            registry_rows=registry_rows,
            equivalencies=equivalencies,
            exact_lookup=exact_lookup,
            loose_lookup=loose_lookup,
        )
        for row in missing_rows
    ]

    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(OUTPUT_CSV, index=False)

    status_counts = Counter(report_df["Status"]) if not report_df.empty else Counter()
    company_counts = Counter(report_df["Missing_Company"]) if not report_df.empty else Counter()
    product_line_counts = Counter(report_df["Missing_Product_Line"]) if not report_df.empty else Counter()

    summary = {
        "report_name": "Enrichment Diagnostic Summary",
        "registries_checked": len(list(REGISTRY_DIR.glob("*.csv"))),
        "total_registry_rows": len(registry_rows),
        "missing_rows_checked": len(missing_rows),
        "auto_fill_same_company": status_counts.get("AUTO_FILL_SAME_COMPANY", 0),
        "auto_fill_equivalency": status_counts.get("AUTO_FILL_EQUIVALENCY", 0),
        "needs_review_or_manual": (
            len(missing_rows)
            - status_counts.get("AUTO_FILL_SAME_COMPANY", 0)
            - status_counts.get("AUTO_FILL_EQUIVALENCY", 0)
        ),
        "status_counts": dict(status_counts),
        "missing_by_company": dict(company_counts),
        "missing_by_product_line": dict(product_line_counts),
        "output_csv": str(OUTPUT_CSV),
        "output_markdown": str(OUTPUT_MD),
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, indent=4)

    markdown = build_markdown_report(
        summary=summary,
        status_counts=status_counts,
        company_counts=company_counts,
        product_line_counts=product_line_counts,
    )

    with open(OUTPUT_MD, "w", encoding="utf-8") as md_file:
        md_file.write(markdown)

    print("ENRICHMENT DIAGNOSTIC REPORT")
    print("----------------------------")
    print(f"Missing rows checked: {len(missing_rows)}")
    print(f"Auto-fill same company: {summary['auto_fill_same_company']}")
    print(f"Auto-fill equivalency: {summary['auto_fill_equivalency']}")
    print(f"Needs review/manual: {summary['needs_review_or_manual']}")
    print()
    print(f"CSV saved to: {OUTPUT_CSV}")
    print(f"JSON saved to: {OUTPUT_JSON}")
    print(f"Markdown saved to: {OUTPUT_MD}")


if __name__ == "__main__":
    main()