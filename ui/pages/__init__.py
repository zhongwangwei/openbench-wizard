# -*- coding: utf-8 -*-
"""Pages package."""

from ui.pages.base_page import BasePage
from ui.pages.page_general import PageGeneral
from ui.pages.page_evaluation import PageEvaluation
from ui.pages.page_metrics import PageMetrics
from ui.pages.page_scores import PageScores
from ui.pages.page_comparisons import PageComparisons
from ui.pages.page_statistics import PageStatistics
from ui.pages.page_ref_data import PageRefData
from ui.pages.page_sim_data import PageSimData
from ui.pages.page_preview import PagePreview
from ui.pages.page_run_monitor import PageRunMonitor

__all__ = [
    "BasePage",
    "PageGeneral",
    "PageEvaluation",
    "PageMetrics",
    "PageScores",
    "PageComparisons",
    "PageStatistics",
    "PageRefData",
    "PageSimData",
    "PagePreview",
    "PageRunMonitor",
]
