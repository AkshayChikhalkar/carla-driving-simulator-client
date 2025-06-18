import pytest
import logging
from datetime import datetime
from pathlib import Path


def pytest_configure(config):
    """Configure pytest"""
    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Configure HTML report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = reports_dir / f"scenario_report_{timestamp}.html"
    config.option.htmlpath = str(html_report)

    # Add custom markers
    config.addinivalue_line("markers", "scenario: mark test as a scenario test")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add custom information to test reports"""
    outcome = yield
    report = outcome.get_result()

    # Add scenario name to report
    if "test_" in item.name:
        scenario_name = item.name.replace("test_", "")
        report.scenario_name = scenario_name

    # Add logs to report
    if report.when == "call":
        report.logs = []
        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                with open(handler.baseFilename, "r") as f:
                    report.logs = f.readlines()


def pytest_html_report_title(report):
    """Customize HTML report title"""
    report.title = "CARLA Driving Simulator - Scenario Test Report"


def pytest_html_results_table_header(cells):
    """Customize HTML report table header"""
    cells.insert(2, "Scenario Name")
    cells.insert(3, "Logs")


def pytest_html_results_table_row(report, cells):
    """Customize HTML report table row"""
    cells.insert(2, f"<td>{getattr(report, 'scenario_name', '')}</td>")

    # Add logs in a collapsible section
    logs = getattr(report, "logs", [])
    if logs:
        log_content = "".join(logs)
        cells.insert(
            3,
            f"<td><details><summary>View Logs</summary><pre>{log_content}</pre></details></td>",
        )
    else:
        cells.insert(3, "<td>No logs available</td>")


def pytest_collection_modifyitems(items):
    """Modify test collection to exclude test_scenarios.py"""
    items[:] = [item for item in items if "test_scenarios" not in item.nodeid]
