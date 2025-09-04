from __future__ import annotations

# Shiny dashboard app for the Tender Intelligence Platform
# Provides a friendly UI to run scans and explore opportunities

import os
from datetime import datetime
from dataclasses import asdict, is_dataclass
from typing import List, Dict, Any

import pandas as pd
from shiny import App, reactive, render, ui
import shinyswatch
from dotenv import load_dotenv

# Lazy import of the platform to avoid failing at app startup if env is missing
PLATFORM = None


def load_monitor():
    """Create and return a configured ActuarialTenderMonitor; raises with helpful message if API key missing."""
    global PLATFORM
    if PLATFORM is None:
        # Defer import so the app can start without a valid .env
        from Tender_Intelligence_Platform import setup_tender_monitoring
        PLATFORM = setup_tender_monitoring()
    return PLATFORM


def dataclass_list_to_df(items: List[Any]) -> pd.DataFrame:
    """Convert a list of dataclass items into a pandas DataFrame with friendly types."""
    if not items:
        return pd.DataFrame()

    def normalize(obj: Dict[str, Any]) -> Dict[str, Any]:
        norm: Dict[str, Any] = {}
        for k, v in obj.items():
            if hasattr(v, "value"):  # Enum
                norm[k] = getattr(v, "value")
            elif isinstance(v, datetime):
                norm[k] = v.isoformat(timespec="seconds")
            elif isinstance(v, list):
                # Convert enums and other basic items to strings
                norm[k] = ", ".join([getattr(x, "value", str(x)) for x in v])
            elif isinstance(v, dict):
                norm[k] = "; ".join(f"{a}: {b}" for a, b in v.items()) if v else ""
            else:
                norm[k] = v
        return norm

    rows = [normalize(asdict(x) if is_dataclass(x) else x) for x in items]
    df = pd.DataFrame(rows)

    # Prefer specific column order if available
    preferred_cols = [
        "title",
        "source_site",
        "client_organization",
        "publication_date",
        "closing_date",
        "status",
        "estimated_value",
        "location",
        "opportunity_score",
        "service_areas_matched",
        "keywords_matched",
        "url",
    ]
    ordered = [c for c in preferred_cols if c in df.columns]
    df = df[ordered + [c for c in df.columns if c not in ordered]]
    return df


# UI definition
app_ui = ui.page_navbar(
    ui.nav(
        "Dashboard",
        ui.layout_sidebar(
            ui.sidebar(
                ui.input_action_button("run_scan", "Run daily scan", class_="btn btn-primary"),
                ui.input_select("score_filter", "Minimum score", choices=["minimal", "low", "medium", "high"], selected="low"),
                ui.input_text("keyword_filter", "Keyword contains", placeholder="actuarial, pension, IFRS 17, ..."),
                ui.input_checkbox("save_report", "Save Markdown report after scan", value=True),
                open=True,
            ),
            ui.layout_columns(
                ui.card(
                    ui.card_header("Overview"),
                    ui.output_ui("kpis"),
                ),
                col_widths=(12,),
            ),
            ui.hr(),
            ui.card(
                ui.card_header("Opportunities"),
                ui.output_ui("opps_table"),
            ),
        ),
    ),
    ui.nav(
        "Details",
        ui.card(
            ui.card_header("Selected Opportunity"),
            ui.output_ui("detail_view"),
        ),
    ),
    title="Tender Intelligence Dashboard",
    theme=shinyswatch.theme.lux(),
)


def server(input, output, session):
    # Reactive store
    opps_df = reactive.Value(pd.DataFrame())
    last_run = reactive.Value(None)

    def filtered_df(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        f = df.copy()
        # Filter by minimum score category
        order = {"minimal": 0, "low": 1, "medium": 2, "high": 3}
        min_sel = input.score_filter()
        if "opportunity_score" in f.columns and min_sel in order:
            f = f[f["opportunity_score"].map(order).fillna(-1) >= order[min_sel]]
        # Keyword filter (in title or description)
        kw = input.keyword_filter().strip()
        if kw:
            mask = (
                f.get("title", "").str.contains(kw, case=False, na=False)
                | f.get("description", "").str.contains(kw, case=False, na=False)
            )
            f = f[mask]
        return f

    @reactive.event(input.run_scan)
    def _run_scan():
        ui.notification_show("Running tender scan... This may take up to a few minutes.", duration=None, id="scan")
        load_dotenv(override=True)
        try:
            monitor = load_monitor()
            # Run scan
            opportunities = monitor.monitor_all_sites()
            # Optionally save report
            if input.save_report():
                monitor.generate_leads_report(opportunities if opportunities is not None else [])
            df = dataclass_list_to_df(opportunities)
            opps_df.set(df)
            last_run.set(datetime.now())
            ui.notification_show(f"Scan complete. Found {len(df)} opportunities.", type="message", duration=5)
        except Exception as e:
            ui.notification_show(f"Scan failed: {e}", type="error", duration=8)
        finally:
            ui.notification_remove("scan")

    @output
    @render.ui
    def kpis():
        df = opps_df()
        total = len(df)
        by_score = df["opportunity_score"].value_counts().to_dict() if not df.empty else {}
        by_site = df["source_site"].value_counts().head(5).to_dict() if not df.empty else {}
        last = last_run()
        return ui.TagList(
            ui.layout_columns(
                ui.card(ui.h4("Total opportunities"), ui.h2(f"{total}")),
                ui.card(ui.h4("By score"), ui.tags.pre("\n".join(f"{k.title()}: {v}" for k, v in by_score.items()) or "-")),
                ui.card(ui.h4("Top sources"), ui.tags.pre("\n".join(f"{k}: {v}" for k, v in by_site.items()) or "-")),
                col_widths=(4, 4, 4),
            ),
            ui.tags.small(f"Last run: {last.strftime('%Y-%m-%d %H:%M:%S')}" if last else "Last run: never"),
        )

    @output
    @render.ui
    def opps_table():
        df = filtered_df(opps_df())
        if df.empty:
            return ui.div("No opportunities yet. Click 'Run daily scan' to start.")
        display_cols = [
            c for c in [
                "title",
                "source_site",
                "client_organization",
                "publication_date",
                "closing_date",
                "status",
                "estimated_value",
                "location",
                "opportunity_score",
                "service_areas_matched",
                "url",
            ]
            if c in df.columns
        ]
        # Add row id for selection
        df = df.reset_index(drop=False).rename(columns={"index": "row_id"})
        html = df[display_cols + ["row_id"]].to_html(index=False, escape=False)
        return ui.TagList(
            ui.input_numeric("detail_id", "View details for row id", value=0, min=0),
            ui.tags.div(ui.HTML(html), style="max-height: 520px; overflow:auto;"),
        )

    @output
    @render.ui
    def detail_view():
        df = filtered_df(opps_df())
        if df.empty:
            return ui.div("No data.")
        rid = input.detail_id() or 0
        if "row_id" not in df.columns:
            df = df.reset_index(drop=False).rename(columns={"index": "row_id"})
        row = df[df["row_id"] == rid]
        if row.empty:
            return ui.div("Select a valid row id from the table above.")
        rec = row.iloc[0].to_dict()
        # Nicely format key fields
        header = ui.h4(rec.get("title", "Opportunity"))
        meta = ui.tags.ul(
            ui.tags.li(f"Source: {rec.get('source_site','')}"),
            ui.tags.li(f"Client: {rec.get('client_organization','')}"),
            ui.tags.li(f"Published: {rec.get('publication_date','')}") ,
            ui.tags.li(f"Closing: {rec.get('closing_date','')}") ,
            ui.tags.li(f"Status: {rec.get('status','')}") ,
            ui.tags.li(f"Score: {rec.get('opportunity_score','')}") ,
            ui.tags.li(f"Service Areas: {rec.get('service_areas_matched','')}") ,
            ui.tags.li(ui.tags.a("Open notice", href=rec.get("url","#"), target="_blank")),
        )
        desc = ui.tags.pre(rec.get("description", ""))
        analysis = rec.get("ai_analysis", None)
        analysis_ui = ui.card(ui.card_header("AI Analysis"), ui.tags.pre(analysis)) if analysis else ui.div()
        return ui.TagList(header, meta, ui.hr(), desc, analysis_ui)


# Build app
app = App(app_ui, server)

if __name__ == "__main__":
    # Allow running: python app.py
    # Load env early so setup_tender_monitoring finds OPENAI_API_KEY when scanning
    load_dotenv(override=True)
    from shiny import run_app
    run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
