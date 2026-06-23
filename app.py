"""Steel Grating Optimizer — Streamlit Application."""

import json
import os
import streamlit as st
import pandas as pd

from csv_importer import parse_csv_dataframe
from processor import process_panels, process_panels_optimized, process_panels_with_recovery, process_panels_with_packing
from product_master import build_product_catalog, SERIES_CONFIG, TYPE_CONFIG, calculate_standard_width
from product_store import (
    add_custom_product, delete_custom_product, load_custom_products,
    hide_product, unhide_product, load_hidden_codes, unhide_all,
)
from models import ProductMaster
from export_pdf import generate_pdf
from export_excel import generate_excel


def _load_depth_map() -> dict[str, float] | None:
    """Load depth_map from depth_map.json if it exists."""
    path = os.path.join(os.path.dirname(__file__), "depth_map.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return None
    return {str(k): float(v) for k, v in data.items()}

VALID_USERS = {
    "admin": "1234",
}


def login_page():
    """Render the login page."""
    st.markdown(
        """
        <div style="text-align:center; padding-top:60px;">
            <h1>🏭 Steel Grating Optimizer</h1>
            <p style="color:gray;">Version 1.2.1</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if username in VALID_USERS and VALID_USERS[username] == password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid username or password.")


def main_app():
    """Render the main application after login."""
    # --- Sidebar ---
    with st.sidebar:
        st.title("🏭 SGO v1.2.1")
        st.caption(f"Logged in as: **{st.session_state.get('username', '')}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")
        page = st.radio("Navigation", ["Import & Process", "Product Catalog"])

    if page == "Product Catalog":
        render_catalog_page()
    else:
        render_import_page()


def render_catalog_page():
    """Display the product master catalog with add/delete functionality."""
    st.header("Product Catalog")

    # --- Show success/error messages from previous action ---
    if "catalog_msg" in st.session_state:
        msg_type, msg_text = st.session_state.pop("catalog_msg")
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "error":
            st.error(msg_text)

    # --- Add New Product ---
    with st.expander("➕ เพิ่มรายการสินค้าใหม่"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            new_code = st.text_input("Product Code", placeholder="e.g. TA140/1", key="add_code")
        with col_b:
            new_series = st.selectbox("Series", [1, 2, 3], key="add_series")
        with col_c:
            new_type = st.selectbox("Type", ["A", "B"], key="add_type")

        col_d, col_e, col_f = st.columns(3)
        s_cfg = SERIES_CONFIG[new_series]
        t_cfg = TYPE_CONFIG[new_type]
        with col_d:
            new_pitch = st.number_input("Load Bar Pitch (mm)", value=s_cfg["load_bar_pitch"], min_value=1.0, key="add_pitch")
        with col_e:
            new_bar_count = st.number_input("Load Bar Count", value=s_cfg["load_bar_count"], min_value=2, key="add_barcount")
        with col_f:
            new_thickness = st.number_input("Thickness (mm)", value=30.0, min_value=1.0, key="add_thick")

        col_g, col_h = st.columns(2)
        with col_g:
            new_cb_pitch = st.number_input("Cross Bar Pitch (mm)", value=t_cfg["cross_bar_pitch"], min_value=1.0, key="add_cbpitch")
        with col_h:
            new_front = st.number_input("Front Length (mm)", value=t_cfg["front_length"], min_value=1.0, key="add_front")

        new_std_width = calculate_standard_width(new_pitch, new_bar_count, new_thickness)
        st.info(f"Standard Width (คำนวณอัตโนมัติ): **{new_std_width:.1f} mm**")

        if st.button("เพิ่มสินค้า", use_container_width=True, type="primary"):
            if not new_code.strip():
                st.session_state["catalog_msg"] = ("error", "กรุณาใส่ Product Code")
            else:
                product = ProductMaster(
                    series=new_series,
                    product_type=new_type,
                    load_bar_pitch=new_pitch,
                    load_bar_count=new_bar_count,
                    cross_bar_pitch=new_cb_pitch,
                    front_length=new_front,
                    load_bar_thickness=new_thickness,
                    standard_width=new_std_width,
                )
                code_upper = new_code.strip().upper()
                add_custom_product(code_upper, product)
                st.session_state["catalog_msg"] = ("success", f"เพิ่ม {code_upper} เรียบร้อยแล้ว")
            st.rerun()

    st.markdown("---")

    # --- Display Catalog with Delete Buttons ---
    catalog = build_product_catalog()
    custom_codes = set(load_custom_products().keys())
    hidden_codes = load_hidden_codes()

    rows = []
    for code, p in catalog.items():
        rows.append({
            "Code": code,
            "Series": p.series,
            "Type": f"T{p.product_type}",
            "Pitch (mm)": p.load_bar_pitch,
            "Bar Count": p.load_bar_count,
            "CB Pitch (mm)": p.cross_bar_pitch,
            "Thickness (mm)": p.load_bar_thickness,
            "Std Width (mm)": p.standard_width,
            "Source": "Custom" if code in custom_codes else "Standard",
        })

    df = pd.DataFrame(rows)

    col1, col2, col3 = st.columns(3)
    with col1:
        series_filter = st.multiselect("Filter by Series", [1, 2, 3], default=[1, 2, 3])
    with col2:
        type_filter = st.multiselect("Filter by Type", ["TA", "TB"], default=["TA", "TB"])
    with col3:
        source_filter = st.multiselect("Filter by Source", ["Standard", "Custom"], default=["Standard", "Custom"])

    filtered = df[
        df["Series"].isin(series_filter)
        & df["Type"].isin(type_filter)
        & df["Source"].isin(source_filter)
    ]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"Total products: {len(filtered)} (Standard: {len(filtered[filtered['Source']=='Standard'])}, Custom: {len(filtered[filtered['Source']=='Custom'])})")

    # --- Delete Section ---
    st.markdown("---")
    with st.expander("🗑️ ลบรายการสินค้า"):
        all_codes = sorted(catalog.keys())
        del_code = st.selectbox("เลือก Product ที่ต้องการลบ", all_codes, key="del_select")

        if del_code:
            is_custom = del_code in custom_codes
            label = "Custom" if is_custom else "Standard"
            st.caption(f"**{del_code}** — {label}")

            if st.button(f"ลบ {del_code}", type="secondary", use_container_width=True):
                if is_custom:
                    delete_custom_product(del_code)
                    st.session_state["catalog_msg"] = ("success", f"ลบ {del_code} (Custom) เรียบร้อยแล้ว")
                else:
                    hide_product(del_code)
                    st.session_state["catalog_msg"] = ("success", f"ซ่อน {del_code} (Standard) เรียบร้อยแล้ว")
                st.rerun()

    # --- Restore hidden products ---
    if hidden_codes:
        with st.expander(f"♻️ กู้คืนรายการที่ซ่อน ({len(hidden_codes)} รายการ)"):
            restore_code = st.selectbox("เลือก Product ที่ต้องการกู้คืน", hidden_codes, key="restore_select")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button(f"กู้คืน {restore_code}", use_container_width=True):
                    unhide_product(restore_code)
                    st.session_state["catalog_msg"] = ("success", f"กู้คืน {restore_code} เรียบร้อยแล้ว")
                    st.rerun()
            with col_r2:
                if st.button("กู้คืนทั้งหมด", use_container_width=True):
                    unhide_all()
                    st.session_state["catalog_msg"] = ("success", f"กู้คืนทั้งหมด {len(hidden_codes)} รายการเรียบร้อยแล้ว")
                    st.rerun()


def render_import_page():
    """Import CSV and process panels."""
    st.header("Import & Process Fabricated Panels")

    st.subheader("1. Upload CSV")
    st.caption("Format: Mark, Product, Width, Length, Qty")

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded is not None:
        try:
            df_raw = pd.read_csv(uploaded)
            st.subheader("2. Raw Data Preview")
            st.dataframe(df_raw, use_container_width=True, hide_index=True)

            panels = parse_csv_dataframe(df_raw)
            if not panels:
                st.error("No valid panels found in CSV.")
                return

            st.success(f"Parsed {len(panels)} panel row(s).")

            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            with col_btn1:
                phase1_btn = st.button("Phase-1: Individual", use_container_width=True)
            with col_btn2:
                phase2_btn = st.button("Phase-2: Optimize", use_container_width=True)
            with col_btn3:
                phase3_btn = st.button("Phase-3: Recovery", use_container_width=True)
            with col_btn4:
                phase32a_btn = st.button("Phase-3.2A: Production Plan", type="primary", use_container_width=True)

            if phase1_btn or phase2_btn or phase3_btn or phase32a_btn:
                for key in ["processed", "summary", "warnings", "opt_summary",
                             "recovery_summary", "validation_report", "recovery_report",
                             "packing_summary", "packing_validation", "packing_report"]:
                    st.session_state.pop(key, None)

                if phase32a_btn:
                    depth_map = _load_depth_map()
                    with st.spinner("Processing with Recovery + Production Cutting Plan..."):
                        result = process_panels_with_packing(panels, depth_map)
                    st.session_state["processed"] = result["processed"]
                    st.session_state["summary"] = result["summary"]
                    st.session_state["opt_summary"] = result["opt_summary"]
                    st.session_state["warnings"] = result["warnings"]
                    st.session_state["recovery_summary"] = result["recovery_summary"]
                    st.session_state["validation_report"] = result["validation_report"]
                    st.session_state["recovery_report"] = result["recovery_report"]
                    st.session_state["packing_summary"] = result["packing_summary"]
                    st.session_state["packing_validation"] = result["packing_validation"]
                    st.session_state["packing_report"] = result["packing_report"]
                elif phase3_btn:
                    depth_map = _load_depth_map()
                    with st.spinner("Processing with Material Recovery..."):
                        result = process_panels_with_recovery(panels, depth_map)
                    st.session_state["processed"] = result["processed"]
                    st.session_state["summary"] = result["summary"]
                    st.session_state["opt_summary"] = result["opt_summary"]
                    st.session_state["warnings"] = result["warnings"]
                    st.session_state["recovery_summary"] = result["recovery_summary"]
                    st.session_state["validation_report"] = result["validation_report"]
                    st.session_state["recovery_report"] = result["recovery_report"]
                elif phase2_btn:
                    with st.spinner("Optimizing project..."):
                        processed, summary, opt_summary, warnings = process_panels_optimized(panels)
                    st.session_state["processed"] = processed
                    st.session_state["summary"] = summary
                    st.session_state["opt_summary"] = opt_summary
                    st.session_state["warnings"] = warnings
                else:
                    with st.spinner("Processing..."):
                        processed, summary, warnings = process_panels(panels)
                    st.session_state["processed"] = processed
                    st.session_state["summary"] = summary
                    st.session_state["warnings"] = warnings

        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return

    if "processed" in st.session_state:
        processed = st.session_state["processed"]
        summary = st.session_state["summary"]
        warnings = st.session_state["warnings"]

        if warnings:
            st.subheader("Warnings")
            for w in warnings:
                st.warning(w)

        st.subheader("3. Project KPI Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Sold Area", f"{summary.total_sold_area:.4f} m²")
        c2.metric("Production Area", f"{summary.total_production_area:.4f} m²")
        c3.metric("Raw Material Area", f"{summary.total_raw_material_area:.4f} m²")

        c4, c5 = st.columns(2)
        c4.metric("Yield", f"{summary.yield_percent:.2f}%")
        c5.metric("Scrap", f"{summary.scrap_percent:.2f}%")

        c6, c7, c8 = st.columns(3)
        c6.metric("Total Panels", summary.total_panels)
        c7.metric("Expansion Panels", summary.expansion_count)
        c8.metric("Reduction Panels", summary.reduction_count)

        c9, c10 = st.columns(2)
        c9.metric("Total Expansion Width", f"{summary.total_expansion_width:.2f} mm")
        c10.metric("Total Reduction Width", f"{summary.total_reduction_width:.2f} mm")

        st.caption("Yield = Sold Area / Raw Material Area | Scrap = 1 - Yield")

        st.subheader("4. Detailed Results")
        result_rows = []
        for p in processed:
            row = {
                "Mark": p.mark,
                "Product": p.product_code,
                "Series": p.series,
                "Type": f"T{p.product_type}",
                "Std Width (mm)": p.standard_width,
                "Fab Width (mm)": p.fabricated_width,
                "Expansion Width (mm)": p.expansion_width if p.needs_expansion else 0,
                "Reduction Width (mm)": p.reduction_width if p.needs_reduction else 0,
                "Fab Length (mm)": p.fabricated_length,
                "Cut Length (mm)": p.cut_length,
                "Qty": p.qty,
                "Sold Area (m²)": round(p.sold_area_m2, 4),
                "Production Area (m²)": round(p.production_area_m2, 4),
                "Raw Material Area (m²)": round(p.raw_material_area_m2, 4),
            }
            if p.pattern:
                row["Rod Qty"] = p.pattern.rod_qty
                row["Mid Length (mm)"] = p.pattern.mid_length
                row["Start (mm)"] = p.pattern.start_length
                row["End (mm)"] = p.pattern.end_length
                row["Rank"] = p.pattern.rank
                row["Selection Reason"] = p.pattern.selection_reason
            else:
                row["Rod Qty"] = "-"
                row["Mid Length (mm)"] = "-"
                row["Start (mm)"] = "-"
                row["End (mm)"] = "-"
                row["Rank"] = "-"
                row["Selection Reason"] = "No valid pattern"
            result_rows.append(row)

        df_result = pd.DataFrame(result_rows)
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        st.subheader("5. Pattern Audit")
        audit_rows = []
        for p in processed:
            audit_rows.append({
                "Mark": p.mark,
                "Rod Qty": p.pattern.rod_qty if p.pattern else "-",
                "Start Length (mm)": p.pattern.start_length if p.pattern else "-",
                "End Length (mm)": p.pattern.end_length if p.pattern else "-",
                "Selection Reason": p.pattern.selection_reason if p.pattern else "No valid pattern",
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

        st.subheader("6. Pattern Details — All Candidates")
        selected_mark = st.selectbox(
            "Select Mark to view all candidate patterns",
            [p.mark for p in processed],
        )
        selected = next((p for p in processed if p.mark == selected_mark), None)
        if selected and selected.all_patterns:
            if selected.pattern:
                st.success(
                    f"**Selected:** Rod={selected.pattern.rod_qty}, "
                    f"Start={selected.pattern.start_length} mm | "
                    f"{selected.pattern.selection_reason}"
                )

            pat_rows = []
            for pat in selected.all_patterns:
                is_selected = (
                    selected.pattern
                    and pat.rod_qty == selected.pattern.rod_qty
                    and pat.start_length == selected.pattern.start_length
                )
                pat_rows.append({
                    "Rank": pat.rank,
                    "Rod Qty": pat.rod_qty,
                    "Mid Length (mm)": pat.mid_length,
                    "Start (mm)": pat.start_length,
                    "End (mm)": pat.end_length,
                    "In 40-45": "Yes" if pat.is_preferred else "-",
                    "Score": pat.score,
                    "": "< SELECTED" if is_selected else "",
                })
            df_pat = pd.DataFrame(pat_rows).sort_values("Rank")
            st.dataframe(df_pat, use_container_width=True, hide_index=True)

            st.caption(
                "**Ranking:** "
                "P1: Start 40-45 mm | "
                "P2: Smallest Start Length | "
                "P3: Max Rod Qty | "
                "P4: Min Waste"
            )
        elif selected:
            st.info("No valid patterns for this panel.")

        # --- Phase-2 Optimization Report ---
        if "opt_summary" in st.session_state:
            opt = st.session_state["opt_summary"]
            st.markdown("---")
            st.header("Phase-2: Project Optimization Report")

            # ============================================
            # 7. Project Optimization Summary (TASK 5)
            # ============================================
            st.subheader("7. Project Optimization Summary")

            o1, o2, o3 = st.columns(3)
            o1.metric("Optimization Mode", opt.optimization_mode)
            o2.metric("Visual Consistency Score", f"{opt.overall_consistency:.1f}")
            o3.metric("Floor Groups", opt.total_floor_groups)

            o4, o5, o6 = st.columns(3)
            o4.metric("Coverage Panels", f"{opt.total_coverage_panels} / {opt.total_panels}")
            o5.metric("Coverage Marks", f"{opt.total_coverage_marks} / {opt.total_marks}")
            o6.metric("Fallback Panels", opt.total_fallback_panels)

            o7, o8, o9 = st.columns(3)
            o7.metric("Fallback Rate", f"{opt.fallback_rate:.1f}%")
            o8.metric("Yield (Individual)", f"{opt.yield_individual:.2f}%")
            o9.metric("Yield (Optimized)", f"{opt.yield_optimized:.2f}%")

            for fg in opt.floor_groups:
                common_label = f"{fg.common_start} mm" if fg.common_start else "N/A"
                pref_label = "Yes" if fg.is_preferred else "No"
                st.markdown(f"- **{fg.group_name}**: Selected Start = {common_label} | Preferred Range = {pref_label}")

            st.caption("Visual Consistency Score = Panels using Common Start / Total Panels × 100 (Range: 0–100)")

            # ============================================
            # 8. Floor Group Detail Report (TASK 3)
            # ============================================
            st.subheader("8. Floor Group Detail Report")
            for fg in opt.floor_groups:
                common_label = f"{fg.common_start} mm" if fg.common_start else "N/A"
                fallback_qty = fg.total_qty - fg.coverage_qty

                with st.expander(f"{fg.group_name} | Common Start = {common_label} | Coverage = {fg.coverage_percent:.1f}%"):
                    st.markdown(f"### Floor Group: {fg.group_name}")
                    st.markdown(f"**Selected Common Start: {common_label}**")

                    fg1, fg2 = st.columns(2)
                    fg1.metric("Coverage (Panels)", f"{fg.coverage_qty} / {fg.total_qty}")
                    fg2.metric("Coverage (Marks)", f"{fg.coverage_marks} / {fg.total_marks}")

                    fg3, fg4 = st.columns(2)
                    fg3.metric("Coverage %", f"{fg.coverage_percent:.1f}%")
                    fg4.metric("Fallback Panels", fallback_qty)

                    fg5, fg6 = st.columns(2)
                    fg5.metric("Preferred Range (40-45 mm)", "Yes" if fg.is_preferred else "No")
                    yield_val = fg.yield_optimized if fg.consistency_status != "REJECTED" else fg.yield_individual
                    fg5_val = yield_val
                    fg5.metric("Yield", f"{fg5_val:.2f}%")
                    scrap_val = round(100.0 - yield_val, 2)
                    fg6.metric("Scrap", f"{scrap_val:.2f}%")

                    # Panels using Common Start
                    if fg.common_start_marks:
                        st.markdown("**Panels Using Common Start:**")
                        st.markdown(", ".join(f"`{m}`" for m in fg.common_start_marks))

                    # Fallback Panels
                    if fg.fallback_marks:
                        st.markdown("**Fallback Panels:**")
                        for fm in fg.fallback_marks:
                            assign = next((a for a in fg.assignments if a.mark == fm), None)
                            reason = assign.reason if assign else "No matching pattern"
                            st.markdown(f"- `{fm}` — {reason}")

                    # Panel Assignment Table
                    if fg.assignments:
                        st.markdown("**Panel Assignment:**")
                        assign_rows = []
                        for a in fg.assignments:
                            assign_rows.append({
                                "Mark": a.mark,
                                "Start (mm)": a.start_length,
                                "Rod Qty": a.rod_qty,
                                "Assignment": a.assignment_type,
                                "Reason": a.reason,
                            })
                        st.dataframe(pd.DataFrame(assign_rows), use_container_width=True, hide_index=True)

            # ============================================
            # 9. Scenario Comparison (TASK 1 + TASK 2)
            # ============================================
            st.subheader("9. Scenario Comparison")
            for fg in opt.floor_groups:
                if not fg.all_scenarios:
                    continue

                st.markdown(f"### Floor Group: {fg.group_name}")

                cand_rows = []
                for sc in fg.all_scenarios:
                    cand_rows.append({
                        "Start (mm)": sc.representative_start,
                        "Coverage %": f"{sc.coverage_percent:.1f}%",
                        "Coverage Qty": sc.coverage_qty,
                        "Preferred?": "Yes" if sc.is_preferred else "No",
                        "Avg Rod Qty": sc.avg_rod_qty,
                        "Yield %": f"{sc.yield_optimized:.2f}%",
                        "Coverage Score": sc.score_breakdown.get("coverage", 0),
                        "Preferred Score": sc.score_breakdown.get("preferred", 0),
                        "Rod Bonus Score": sc.score_breakdown.get("rod_bonus", 0),
                        "Yield Score": sc.score_breakdown.get("yield", 0),
                        "Total Score": sc.score,
                        "Selected": "YES" if sc.selected else "NO",
                        "Reason": "Selected" if sc.selected else sc.rejection_reason,
                    })
                df_cand = pd.DataFrame(cand_rows)
                st.dataframe(df_cand, use_container_width=True, hide_index=True)

                st.caption(
                    "**Score Formula:** Coverage (1000 × coverage%) + "
                    "Preferred (500 if 40-45mm) + "
                    "Rod Bonus (0.5 × avg rod qty) + "
                    "Yield (50 × yield%) + "
                    "Fallback (-100 per fallback mark)"
                )

                # Decision Explanation
                best = next((sc for sc in fg.all_scenarios if sc.selected), None)
                if best:
                    st.markdown("**Optimization Decision Summary**")
                    yield_impact = round(best.yield_optimized - fg.yield_individual, 2) if fg.yield_individual else 0.0
                    st.markdown(
                        f"- **Selected Start** = {best.representative_start} mm\n"
                        f"- **Coverage** = {best.coverage_percent:.1f}%\n"
                        f"- **Preferred Range (40–45 mm)** = {'Yes' if best.is_preferred else 'No'}\n"
                        f"- **Yield Impact** = {yield_impact:+.2f}%\n"
                        f"- **Fallback Required** = {'Yes' if best.fallback_count > 0 else 'No'}"
                        f"{f' ({best.fallback_count} marks)' if best.fallback_count > 0 else ''}\n"
                        f"- **Final Score** = {best.score}\n\n"
                        f"**Decision:** Highest project consistency."
                    )
                st.markdown("---")

            # ============================================
            # 10. Phase-2 Validation (TASK 4)
            # ============================================
            st.subheader("10. Phase-2 Validation")

            validation_rules = _run_validation(opt, processed, summary)
            all_pass = all(r["status"] == "PASS" for r in validation_rules)

            if all_pass:
                st.success("PHASE-2 VALIDATION: PASS")
            else:
                st.error("PHASE-2 VALIDATION: FAIL")

            val_rows = []
            for r in validation_rules:
                val_rows.append({
                    "Rule": r["rule"],
                    "Description": r["description"],
                    "Status": r["status"],
                    "Detail": r["detail"],
                })
            st.dataframe(pd.DataFrame(val_rows), use_container_width=True, hide_index=True)

        # --- Phase-3: Material Recovery Report ---
        if "recovery_report" in st.session_state:
            report = st.session_state["recovery_report"]
            rec_summary = st.session_state["recovery_summary"]
            val_report = st.session_state["validation_report"]

            st.markdown("---")
            st.header("Phase-3: Material Recovery Report")

            # ============================================
            # 11. Recovery Status (visible by default)
            # ============================================
            st.subheader("11. Recovery Status")

            exec_sum = report["executive_summary"]
            if exec_sum["recovery_status"] == "VALID":
                st.success(
                    f"**VALID** — {exec_sum['validation_passed']} / "
                    f"{exec_sum['validation_total']} PASS"
                )
            else:
                st.error(
                    f"**INVALID** — {exec_sum['validation_passed']} / "
                    f"{exec_sum['validation_total']} PASS"
                )

            r1, r2, r3 = st.columns(3)
            r1.metric("Frozen Yield", f"{exec_sum['frozen_yield']:.2f}%")
            r2.metric("Recovery Rate", f"{exec_sum['recovery_rate']:.2f}%")
            r3.metric("Validation", f"{exec_sum['validation_passed']}/{exec_sum['validation_total']} PASS")

            r4, r5, r6 = st.columns(3)
            r4.metric("Recovered Area", f"{exec_sum['recovered_area_m2']:.4f} m²")
            r5.metric("Dead Scrap Area", f"{exec_sum['dead_scrap_area_m2']:.4f} m²")
            r6.metric("Remaining Stock", f"{exec_sum['remaining_stock_area_m2']:.4f} m²")

            r7, r8 = st.columns(2)
            r7.metric("Total Matches", exec_sum["total_matches"])
            r8.metric("Unmatched Demands", exec_sum["total_unmatched"])

            # ============================================
            # 12. Scrap Inventory (inside expander)
            # ============================================
            inv = report["inventory_summary"]
            with st.expander("12. Scrap Inventory"):
                i1, i2, i3, i4 = st.columns(4)
                i1.metric("Stock Pieces", inv["total_stock_pieces"])
                i2.metric("Available", inv["available_stock_pieces"])
                i3.metric("Depleted", inv["depleted_stock_pieces"])
                i4.metric("Dead Scrap", inv["total_dead_scrap_pieces"])

                if inv["stock_pieces"]:
                    st.markdown("**Stock Pieces**")
                    sp_rows = []
                    for sp in inv["stock_pieces"]:
                        mck = sp["mck"]
                        sp_rows.append({
                            "Piece ID": sp["piece_id"],
                            "Source Mark": sp["source_mark"],
                            "Product": sp["product_code"],
                            "MCK": f"({mck[0]}, {mck[1]}, {mck[2]})",
                            "Original Width (mm)": sp["original_width"],
                            "Remaining Width (mm)": sp["remaining_width"],
                            "Length (mm)": sp["length"],
                            "Qty": sp["qty"],
                            "Status": sp["status"],
                        })
                    st.dataframe(pd.DataFrame(sp_rows), use_container_width=True, hide_index=True)

                if inv["dead_scrap"]:
                    st.markdown("**Dead Scrap**")
                    ds_rows = []
                    for ds in inv["dead_scrap"]:
                        ds_rows.append({
                            "Scrap ID": ds["scrap_id"],
                            "Source Mark": ds["source_mark"],
                            "Width (mm)": ds["width"],
                            "Length (mm)": ds["length"],
                            "Area (m²)": ds["area_m2"],
                            "Qty": ds["qty"],
                            "Origin": ds["origin"],
                            "Reason": ds["reason"],
                        })
                    st.dataframe(pd.DataFrame(ds_rows), use_container_width=True, hide_index=True)

            # ============================================
            # 13. Recovery Matching (inside expander)
            # ============================================
            with st.expander("13. Recovery Matching"):
                match_data = report["match_summary"]
                if match_data:
                    st.markdown("**Matched Demands**")
                    m_rows = []
                    for m in match_data:
                        m_rows.append({
                            "Demand Mark": m["demand_mark"],
                            "Product": m["demand_product_code"],
                            "Expansion (mm)": m["expansion_width"],
                            "Length (mm)": m["demand_length"],
                            "Qty": m["demand_qty"],
                            "Stock Piece": m["stock_piece_id"],
                            "Source Mark": m["source_mark"],
                            "Width Before (mm)": m["stock_width_before"],
                            "Width After (mm)": m["stock_width_after"],
                            "Trim (mm)": m["trim_waste"],
                            "Post Class": m["post_consumption_class"],
                            "Candidates": m["candidate_count"],
                            "Decision": m["decision_reason"],
                        })
                    st.dataframe(pd.DataFrame(m_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No matches found.")

                unmatched_data = report["unmatched_summary"]
                if unmatched_data:
                    st.markdown("**Unmatched Demands**")
                    u_rows = []
                    for u in unmatched_data:
                        u_rows.append({
                            "Mark": u["mark"],
                            "Product": u["product_code"],
                            "Expansion (mm)": u["expansion_width"],
                            "Length (mm)": u["fabricated_length"],
                            "Qty": u["qty"],
                            "Reason": u["reason"],
                        })
                    st.dataframe(pd.DataFrame(u_rows), use_container_width=True, hide_index=True)
                else:
                    st.success("All expansion demands matched.")

            # ============================================
            # 14. Recovery Validation (visible by default)
            # ============================================
            st.subheader("14. Recovery Validation (R10-R21)")

            val_data = report["validation_summary"]
            if val_data["all_passed"]:
                st.success(
                    f"**VALID** — {val_data['passed']} / {val_data['total_rules']} PASS"
                )
            else:
                st.error(
                    f"**INVALID** — {val_data['passed']} / {val_data['total_rules']} PASS"
                )

            v_rows = []
            for r in val_data["rules"]:
                v_rows.append({
                    "Rule": r["rule_id"],
                    "Description": r["description"],
                    "Status": r["status"],
                    "Detail": r["detail"],
                })
            st.dataframe(pd.DataFrame(v_rows), use_container_width=True, hide_index=True)

            # ============================================
            # 15. Recovery Explainability (inside expander)
            # ============================================
            explain_data = report["explainability"]
            if explain_data:
                with st.expander("15. Recovery Explainability"):
                    for entry in explain_data:
                        etype = entry["type"]
                        demand = entry["demand_mark"]
                        stock = entry.get("stock_piece_id", "")

                        if etype == "MATCH_APPROVED":
                            label = f"MATCH APPROVED: {demand} -> {stock}"
                        elif etype == "MATCH_REJECTED":
                            label = f"MATCH REJECTED: {demand} -> {stock}"
                        elif etype == "INVENTORY_RECLASSIFIED":
                            label = f"RECLASSIFIED: {stock}"
                        elif etype == "UNMATCHED":
                            label = f"UNMATCHED: {demand}"
                        else:
                            label = f"{etype}: {demand}"

                        with st.expander(label):
                            st.code(entry["text"], language=None)

        # --- Phase-3.2A: Production Cutting Plan ---
        if "packing_report" in st.session_state:
            packing_rpt = st.session_state["packing_report"]
            packing_sum = st.session_state["packing_summary"]
            packing_val = st.session_state["packing_validation"]

            st.markdown("---")
            st.header("Phase-3.2A: Production Cutting Plan")

            # ============================================
            # 16. Packing KPI Summary
            # ============================================
            st.subheader("16. Packing KPI Summary")

            pk_summary = packing_rpt["summary"]

            pk1, pk2, pk3 = st.columns(3)
            pk1.metric("Algorithm", pk_summary["algorithm"])
            pk2.metric("Stock Lengths Before", pk_summary["stock_lengths_before"])
            pk3.metric("Stock Lengths After", pk_summary["stock_lengths_after"])

            pk4, pk5, pk6 = st.columns(3)
            pk4.metric("Stock Savings", f"{pk_summary['stock_savings']} ({pk_summary['stock_savings_percent']:.2f}%)")
            pk5.metric("Utilization Rate", f"{pk_summary['stock_utilization_rate']:.2f}%")
            pk6.metric("Exact Fit Bins", pk_summary["total_exact_fit_bins"])

            pk7, pk8, pk9 = st.columns(3)
            pk7.metric("Raw Material Area", f"{pk_summary['total_raw_material_area_m2']:.4f} m²")
            pk8.metric("Product Area", f"{pk_summary['total_product_area_m2']:.4f} m²")
            pk9.metric("Waste Area", f"{pk_summary['total_waste_area_m2']:.4f} m²")

            pk10, pk11, pk12 = st.columns(3)
            pk10.metric("Kerf Loss", f"{pk_summary['total_kerf_loss_m2']:.4f} m²")
            pk11.metric("Reusable Remnant", f"{pk_summary['total_reusable_remnant_area_m2']:.4f} m²")
            pk12.metric("Length Waste", f"{pk_summary['total_length_waste_m2']:.4f} m²")

            st.caption(
                f"Total Bins: {pk_summary['total_bins']} | "
                f"Items Packed: {pk_summary['total_items_packed']} | "
                f"Marks Packed: {pk_summary['total_marks_packed']}"
            )

            # ============================================
            # 17. Production Cutting Plan
            # ============================================
            st.subheader("17. Production Cutting Plan")

            cutting_plan = packing_rpt["cutting_plan"]
            cp_rows = []
            for cp in cutting_plan:
                entry_labels = []
                notes = []
                for e in cp["entries"]:
                    entry_labels.append(f"{e['mark']} x {e['qty']}")
                    if e.get("note"):
                        notes.append(f"{e['mark']}: {e['note']}")
                marks_text = ", ".join(entry_labels)
                note_text = "; ".join(notes)

                cp_rows.append({
                    "Bar": cp["bin_id"],
                    "Width (mm)": str(cp["stock_width"]) if cp.get("stock_width") is not None else "",
                    "Marks": marks_text,
                    "Panels": str(cp["total_panels"]) if cp.get("total_panels") is not None else "",
                    "Used (mm)": str(cp["total_used"]) if cp.get("total_used") is not None else "",
                    "Remnant (mm)": str(cp["remnant_length"]) if cp.get("remnant_length") is not None else "",
                    "Classification": cp["remnant_classification"],
                    "Note": note_text,
                })
            st.dataframe(pd.DataFrame(cp_rows), use_container_width=True, hide_index=True)

            with st.expander("Production Format (Copy/Paste)"):
                for cp in cutting_plan:
                    st.text(cp["display"])

            # ============================================
            # 18. Packing Validation (R22-R29)
            # ============================================
            st.subheader("18. Packing Validation (R22-R29)")

            pv_data = packing_rpt["validation"]
            if pv_data["all_passed"]:
                st.success(f"**VALID** — {pv_data['passed']} / {pv_data['total']} PASS")
            else:
                st.error(f"**INVALID** — {pv_data['passed']} / {pv_data['total']} PASS")

            pv_rows = []
            for r in pv_data["rules"]:
                pv_rows.append({
                    "Rule": r["rule_id"],
                    "Description": r["description"],
                    "Status": r["status"],
                    "Detail": r["detail"],
                })
            st.dataframe(pd.DataFrame(pv_rows), use_container_width=True, hide_index=True)

        # --- Export Section ---
        st.markdown("---")
        st.subheader("Export")

        if "packing_report" in st.session_state:
            exp1, exp2, exp3 = st.columns(3)

            with exp1:
                pdf_bytes = generate_pdf(
                    summary=summary,
                    packing_report=st.session_state["packing_report"],
                    packing_summary=st.session_state["packing_summary"],
                    recovery_summary=st.session_state.get("recovery_summary"),
                )
                st.download_button(
                    "Export PDF",
                    pdf_bytes,
                    file_name="Production_Cutting_Plan.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )

            with exp2:
                xlsx_bytes = generate_excel(
                    summary=summary,
                    packing_report=st.session_state["packing_report"],
                    packing_summary=st.session_state["packing_summary"],
                    recovery_summary=st.session_state.get("recovery_summary"),
                )
                st.download_button(
                    "Export Excel",
                    xlsx_bytes,
                    file_name="Production_Cutting_Plan.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )

            with exp3:
                csv_export = df_result.to_csv(index=False)
                st.download_button(
                    "Export CSV",
                    csv_export,
                    file_name="sgo_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        else:
            csv_export = df_result.to_csv(index=False)
            st.download_button(
                "Export CSV",
                csv_export,
                file_name="sgo_results.csv",
                mime="text/csv",
            )


def _run_validation(opt, processed, summary) -> list[dict]:
    """Run 8 engineering validation rules against optimization results."""
    rules = []

    # Rule 1: Selected Start Exists
    starts_exist = all(fg.common_start is not None for fg in opt.floor_groups if fg.consistency_status != "REJECTED")
    rules.append({
        "rule": "Rule 1",
        "description": "Selected Start Exists",
        "status": "PASS" if starts_exist else "FAIL",
        "detail": "All floor groups have a selected common start" if starts_exist else "Missing common start in one or more groups",
    })

    # Rule 2: Selected Start Appears In Scenario Table
    start_in_table = True
    detail_r2 = []
    for fg in opt.floor_groups:
        if fg.common_start is None:
            continue
        scenario_starts = [sc.representative_start for sc in fg.all_scenarios]
        if fg.common_start not in scenario_starts:
            start_in_table = False
            detail_r2.append(f"{fg.group_name}: Start {fg.common_start} mm not in scenario table")
    rules.append({
        "rule": "Rule 2",
        "description": "Selected Start Appears In Scenario Table",
        "status": "PASS" if start_in_table else "FAIL",
        "detail": "All selected starts appear in scenario comparison" if start_in_table else "; ".join(detail_r2),
    })

    # Rule 3: Coverage >= 90%
    coverage_ok = opt.overall_consistency >= 90.0
    rules.append({
        "rule": "Rule 3",
        "description": "Coverage >= 90%",
        "status": "PASS" if coverage_ok else "FAIL",
        "detail": f"Overall consistency = {opt.overall_consistency:.1f}%",
    })

    # Rule 4: Fallback Rate <= 10%
    fallback_ok = opt.fallback_rate <= 10.0
    rules.append({
        "rule": "Rule 4",
        "description": "Fallback Rate <= 10%",
        "status": "PASS" if fallback_ok else "FAIL",
        "detail": f"Fallback rate = {opt.fallback_rate:.1f}%",
    })

    # Rule 5: Visual Consistency >= 80%
    visual_ok = opt.overall_consistency >= 80.0
    rules.append({
        "rule": "Rule 5",
        "description": "Visual Consistency >= 80%",
        "status": "PASS" if visual_ok else "FAIL",
        "detail": f"Visual consistency = {opt.overall_consistency:.1f}%",
    })

    # Rule 6: Yield Calculated
    yield_ok = opt.yield_optimized > 0
    rules.append({
        "rule": "Rule 6",
        "description": "Yield Calculated",
        "status": "PASS" if yield_ok else "FAIL",
        "detail": f"Yield = {opt.yield_optimized:.2f}%",
    })

    # Rule 7: Raw Material Area >= Production Area
    rawmat_ok = summary.total_raw_material_area >= summary.total_production_area
    rules.append({
        "rule": "Rule 7",
        "description": "Raw Material Area >= Production Area",
        "status": "PASS" if rawmat_ok else "FAIL",
        "detail": f"Raw Material = {summary.total_raw_material_area:.4f} m², Production = {summary.total_production_area:.4f} m²",
    })

    # Rule 8: No Missing Candidate Data
    missing = False
    missing_detail = []
    for fg in opt.floor_groups:
        for sc in fg.all_scenarios:
            if sc.representative_start <= 0:
                missing = True
                missing_detail.append(f"{fg.group_name}: scenario with start <= 0")
            if sc.score == 0 and sc.coverage_percent == 0:
                missing = True
                missing_detail.append(f"{fg.group_name}: scenario with zero score and zero coverage")
    rules.append({
        "rule": "Rule 8",
        "description": "No Missing Candidate Data",
        "status": "PASS" if not missing else "FAIL",
        "detail": "All candidate data complete" if not missing else "; ".join(missing_detail),
    })

    # Rule 9: Candidate Count in Pattern Details = Candidate Count in Scenario Comparison
    count_ok = True
    count_detail = []
    for fg in opt.floor_groups:
        # Get all unique starts from Pattern Details (all_patterns of panels in this group)
        group_panels = [p for p in processed if p.product_code == fg.group_name]
        pattern_starts = set()
        for p in group_panels:
            for pat in p.all_patterns:
                pattern_starts.add(pat.start_length)
        # Get all starts from Scenario Comparison
        scenario_starts = set(sc.representative_start for sc in fg.all_scenarios)

        if pattern_starts != scenario_starts:
            count_ok = False
            missing_in_scenario = pattern_starts - scenario_starts
            extra_in_scenario = scenario_starts - pattern_starts
            detail_parts = [f"{fg.group_name}: Pattern Details={len(pattern_starts)}, Scenario={len(scenario_starts)}"]
            if missing_in_scenario:
                detail_parts.append(f"missing in scenario: {sorted(missing_in_scenario)}")
            if extra_in_scenario:
                detail_parts.append(f"extra in scenario: {sorted(extra_in_scenario)}")
            count_detail.append("; ".join(detail_parts))
        else:
            count_detail.append(f"{fg.group_name}: {len(pattern_starts)} candidates match")

    rules.append({
        "rule": "Rule 9",
        "description": "Candidate Count: Pattern Details = Scenario Comparison",
        "status": "PASS" if count_ok else "FAIL",
        "detail": "; ".join(count_detail),
    })

    return rules


def main():
    st.set_page_config(
        page_title="Steel Grating Optimizer",
        page_icon="🏭",
        layout="wide",
    )
    if st.session_state.get("authenticated"):
        main_app()
    else:
        login_page()


if __name__ == "__main__":
    main()
