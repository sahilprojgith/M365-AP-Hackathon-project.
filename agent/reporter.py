import json
import os
from datetime import datetime
from utils.logger import log


class Reporter:
    def __init__(self, test_results, memory, page_map):
        self.test_results = test_results
        self.memory = memory
        self.page_map = page_map
        self.report_dir = "reports"
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_all(self):
        log("=" * 60)
        log("GENERATING REPORTS")
        log("=" * 60)
        self._generate_json()
        self._generate_html()
        log("All reports generated")

    def _generate_json(self):
        passed = [t for t in self.test_results if t["status"] == "PASS"]
        failed = [t for t in self.test_results if t["status"] == "FAIL"]
        skipped = [t for t in self.test_results if t["status"] == "SKIP"]

        categories = {}
        for t in self.test_results:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
            categories[cat][t["status"].lower()] = categories[cat].get(t["status"].lower(), 0) + 1

        report = {
            "timestamp": datetime.now().isoformat(),
            "session": self.memory.data["sessions"],
            "summary": {
                "total_tests": len(self.test_results),
                "passed": len(passed),
                "failed": len(failed),
                "skipped": len(skipped),
                "pass_rate": f"{round(len(passed)/len(self.test_results)*100, 1)}%" if self.test_results else "0%"
            },
            "categories": categories,
            "all_results": self.test_results,
            "page_map": [{"page_name": p["page_name"], "url": p["url"]} for p in self.page_map],
            "memory_snapshot": {
                "sessions": self.memory.data["sessions"],
                "skills": len(self.memory.data.get("learned_skills", [])),
                "selectors": len(self.memory.data.get("working_selectors", {})),
                "pages": len(self.memory.data.get("known_pages", []))
            }
        }

        path = os.path.join(self.report_dir, "test_report.json")
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        log(f"JSON report saved: {path}")

    def _generate_html(self):
        passed = len([t for t in self.test_results if t["status"] == "PASS"])
        failed = len([t for t in self.test_results if t["status"] == "FAIL"])
        skipped = len([t for t in self.test_results if t["status"] == "SKIP"])
        total = len(self.test_results)
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0
        session = self.memory.data["sessions"]
        skills = len(self.memory.data.get("learned_skills", []))
        selectors = len(self.memory.data.get("working_selectors", {}))
        pages = len(self.memory.data.get("known_pages", []))

        # Category data
        categories = {}
        for t in self.test_results:
            cat = t["category"]
            if cat not in categories:
                categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
            status_key = t["status"].lower()
            categories[cat][status_key] = categories[cat].get(status_key, 0) + 1

        cat_labels = list(categories.keys())
        cat_pass = [categories[c]["pass"] for c in cat_labels]
        cat_fail = [categories[c]["fail"] for c in cat_labels]

        # Category colors for color-coded rows
        category_colors = {
            "Login": "#64b5f6",
            "Navigation": "#00e676",
            "Button": "#ffab00",
            "Input": "#ce93d8",
            "CrossNav": "#4fc3f7",
            "Structure": "#ff8a65",
            "DeepFunctional": "#ef5350",
            "Logout": "#9575cd"
        }

        # LLM analysis
        llm_text = ""
        for skill in self.memory.data.get("learned_skills", []):
            if skill["name"] == "llm_analysis":
                llm_text = skill.get("steps", {}).get("analysis", "")
        if not llm_text:
            llm_text = "No LLM analysis available for this session."

        llm_escaped = json.dumps(llm_text)

        # Failed tests
        failed_tests = [t for t in self.test_results if t["status"] == "FAIL"]

        failed_rows = ""
        for t in failed_tests:
            border_color = category_colors.get(t['category'], '#555')
            failed_rows += f"""
            <tr style="border-left: 4px solid {border_color};">
                <td>{t['id']}</td>
                <td>{t['name']}</td>
                <td><span class="cat-badge" style="background:{border_color}20; color:{border_color};">{t['category']}</span></td>
                <td><span class="badge badge-fail">FAIL</span></td>
                <td>{t['details']}</td>
            </tr>"""

        if not failed_rows:
            failed_section = """
            <div class="success-banner">
                <span class="success-icon">🎉</span>
                <span>All tests passed! No failures detected.</span>
            </div>"""
        else:
            failed_section = f"""
            <table class="results-table">
                <thead>
                    <tr><th>ID</th><th>Test Name</th><th>Category</th><th>Status</th><th>Details</th></tr>
                </thead>
                <tbody>{failed_rows}</tbody>
            </table>"""

        # All tests table with color-coded rows
        all_rows = ""
        for t in self.test_results:
            status_class = "badge-pass" if t["status"] == "PASS" else "badge-fail" if t["status"] == "FAIL" else "badge-skip"
            icon = "✅" if t["status"] == "PASS" else "❌" if t["status"] == "FAIL" else "⏭️"
            priority_badge = ' <span class="badge badge-priority">HIGH</span>' if t.get("priority") == "HIGH" else ""
            border_color = category_colors.get(t['category'], '#555')
            all_rows += f"""
            <tr class="test-row" data-status="{t['status']}" data-category="{t['category']}" style="border-left: 4px solid {border_color};">
                <td>{t['id']}</td>
                <td>{t['name']}{priority_badge}</td>
                <td><span class="cat-badge" style="background:{border_color}20; color:{border_color};">{t['category']}</span></td>
                <td><span class="badge {status_class}">{icon} {t['status']}</span></td>
                <td>{t['details']}</td>
            </tr>"""

        # Memory skills
        skills_list = ""
        for s in self.memory.data.get("learned_skills", [])[:15]:
            skills_list += f"""
            <div class="skill-chip">
                <span class="skill-icon">🎯</span>
                <span>{s['name']}</span>
                <span class="skill-count">×{s.get('times_used', 1)}</span>
            </div>"""

        # Known selectors
        selectors_html = ""
        for field, sel in self.memory.data.get("working_selectors", {}).items():
            selectors_html += f"""
            <div class="selector-item">
                <span class="selector-field">{field}</span>
                <span class="selector-arrow">→</span>
                <code>{sel}</code>
            </div>"""

        # Known pages
        pages_html = ""
        for p in self.memory.data.get("known_pages", []):
            pages_html += f"""
            <div class="page-item">
                <span class="page-icon">🌐</span>
                <span class="page-name">{p.get('name', 'Unknown')}</span>
            </div>"""

        # Health
        if pass_rate == 100:
            health_color = "#00e676"
            health_text = "EXCELLENT"
            health_emoji = "🟢"
        elif pass_rate >= 90:
            health_color = "#76ff03"
            health_text = "GOOD"
            health_emoji = "🟡"
        elif pass_rate >= 70:
            health_color = "#ffab00"
            health_text = "WARNING"
            health_emoji = "🟠"
        else:
            health_color = "#ff1744"
            health_text = "CRITICAL"
            health_emoji = "🔴"

        # SVG progress ring calculations
        ring_radius = 80
        ring_circumference = 2 * 3.14159 * ring_radius
        ring_offset = ring_circumference - (pass_rate / 100) * ring_circumference

        # Category legend for color reference
        cat_legend = ""
        for cat in cat_labels:
            color = category_colors.get(cat, '#555')
            cat_legend += f'<span class="cat-legend-item"><span class="cat-dot" style="background:{color};"></span>{cat}</span>'

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>APA Testing Agent — Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0d1230 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}

        .dashboard {{ max-width: 1400px; margin: 0 auto; }}

        /* Header */
        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #1e2a5e, #2d3a7e);
            border-radius: 16px;
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        .header h1 {{ font-size: 28px; color: #fff; margin-bottom: 8px; }}
        .header .subtitle {{ color: #8892b0; font-size: 14px; }}
        .header .health {{
            display: inline-block; margin-top: 12px; padding: 6px 20px;
            border-radius: 20px; font-weight: bold; font-size: 14px;
            color: #000; background: {health_color};
        }}

        /* Progress Ring Section */
        .ring-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 60px;
            margin-bottom: 24px;
            padding: 30px;
            background: linear-gradient(135deg, #1a2040, #252b50);
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            flex-wrap: wrap;
        }}

        .ring-container {{
            position: relative;
            width: 200px;
            height: 200px;
        }}

        .ring-svg {{
            transform: rotate(-90deg);
            filter: drop-shadow(0 0 12px {health_color}40);
        }}

        .ring-bg {{
            fill: none;
            stroke: rgba(255,255,255,0.08);
            stroke-width: 12;
        }}

        .ring-progress {{
            fill: none;
            stroke: {health_color};
            stroke-width: 12;
            stroke-linecap: round;
            stroke-dasharray: {ring_circumference};
            stroke-dashoffset: {ring_circumference};
            transition: stroke-dashoffset 2s ease-out;
        }}

        .ring-text {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }}

        .ring-percent {{
            font-size: 42px;
            font-weight: bold;
            color: {health_color};
            display: block;
        }}

        .ring-label {{
            font-size: 12px;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .ring-stats {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .ring-stat {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .ring-stat-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .ring-stat-info {{
            display: flex;
            flex-direction: column;
        }}

        .ring-stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }}

        .ring-stat-label {{
            font-size: 12px;
            color: #8892b0;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #1a2040, #252b50);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-4px);
        }}

        .stat-card .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 4px;
        }}

        .stat-card .stat-label {{
            font-size: 13px;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .glow-blue {{ box-shadow: 0 4px 20px rgba(100,181,246,0.25); }}
        .glow-green {{ box-shadow: 0 4px 20px rgba(0,230,118,0.25); }}
        .glow-red {{ box-shadow: 0 4px 20px rgba(255,23,68,0.25); }}
        .glow-gold {{ box-shadow: 0 4px 20px rgba(255,171,0,0.25); }}
        .glow-purple {{ box-shadow: 0 4px 20px rgba(206,147,216,0.25); }}
        .glow-cyan {{ box-shadow: 0 4px 20px rgba(79,195,247,0.25); }}

        .stat-total {{ color: #64b5f6; }}
        .stat-passed {{ color: #00e676; }}
        .stat-failed {{ color: #ff1744; }}
        .stat-rate {{ color: #ffab00; }}
        .stat-session {{ color: #ce93d8; }}
        .stat-skills {{ color: #4fc3f7; }}

        /* Section */
        .section {{
            background: linear-gradient(135deg, #1a2040, #1e2550);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}

        .section-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
            color: #fff;
        }}

        /* Charts */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 24px;
            margin-bottom: 24px;
        }}

        .chart-container {{
            background: linear-gradient(135deg, #1a2040, #1e2550);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}

        .chart-title {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 16px;
            color: #fff;
        }}

        /* Tables */
        .results-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 4px;
            font-size: 13px;
        }}

        .results-table thead tr {{
            background: rgba(100, 181, 246, 0.15);
        }}

        .results-table th {{
            padding: 12px;
            text-align: left;
            color: #64b5f6;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .results-table td {{
            padding: 10px 12px;
            background: rgba(255,255,255,0.02);
        }}

        .results-table tbody tr {{
            transition: background 0.2s;
        }}

        .results-table tbody tr:hover {{
            background: rgba(255,255,255,0.05);
        }}

        /* Category badge */
        .cat-badge {{
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        }}

        /* Category legend */
        .cat-legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
        }}

        .cat-legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #aaa;
        }}

        .cat-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}

        /* Badges */
        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}

        .badge-pass {{ background: rgba(0,230,118,0.15); color: #00e676; }}
        .badge-fail {{ background: rgba(255,23,68,0.15); color: #ff1744; }}
        .badge-skip {{ background: rgba(255,171,0,0.15); color: #ffab00; }}
        .badge-priority {{ background: rgba(255,171,0,0.2); color: #ffab00; margin-left: 8px; font-size: 10px; }}

        /* Success Banner */
        .success-banner {{
            background: linear-gradient(135deg, rgba(0,230,118,0.1), rgba(0,230,118,0.05));
            border: 1px solid rgba(0,230,118,0.3);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            font-size: 16px;
            color: #00e676;
        }}
        .success-icon {{ font-size: 32px; margin-right: 12px; }}

        /* LLM Section with typing */
        .llm-content {{
            background: rgba(206,147,216,0.05);
            border: 1px solid rgba(206,147,216,0.2);
            border-radius: 8px;
            padding: 16px;
            font-size: 13px;
            line-height: 1.8;
            color: #ccc;
            min-height: 60px;
            position: relative;
        }}

        .llm-cursor {{
            display: inline-block;
            width: 2px;
            height: 16px;
            background: #ce93d8;
            margin-left: 2px;
            vertical-align: middle;
            animation: blink 0.8s infinite;
        }}

        @keyframes blink {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0; }}
        }}

        .llm-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #7c4dff, #ce93d8);
            color: #fff;
            padding: 3px 10px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 8px;
            letter-spacing: 0.5px;
        }}

        /* Skills */
        .skills-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .skill-chip {{
            background: rgba(79,195,247,0.1);
            border: 1px solid rgba(79,195,247,0.3);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: transform 0.2s;
        }}

        .skill-chip:hover {{ transform: scale(1.05); }}
        .skill-icon {{ font-size: 14px; }}
        .skill-count {{ color: #4fc3f7; font-weight: bold; }}

        /* Selectors */
        .selector-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            margin-bottom: 4px;
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
        }}

        .selector-field {{
            color: #64b5f6;
            font-weight: bold;
            min-width: 80px;
        }}

        .selector-arrow {{ color: #555; }}

        .selector-item code {{
            background: rgba(0,0,0,0.3);
            padding: 2px 8px;
            border-radius: 4px;
            color: #00e676;
            font-size: 12px;
        }}

        /* Pages */
        .page-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
        }}

        .page-icon {{ font-size: 16px; }}
        .page-name {{ color: #ccc; }}

        /* Filter bar */
        .filter-bar {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            padding: 6px 16px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.2);
            background: transparent;
            color: #ccc;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }}

        .filter-btn:hover, .filter-btn.active {{
            background: rgba(100,181,246,0.2);
            border-color: #64b5f6;
            color: #64b5f6;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 20px;
            color: #555;
            font-size: 12px;
        }}

        @media (max-width: 768px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .ring-section {{ flex-direction: column; gap: 30px; }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">

        <!-- Header -->
        <div class="header">
            <h1>🤖 APA Testing Agent — Dashboard</h1>
            <div class="subtitle">Hermes-Inspired Autonomous Testing • Weatherseal 360 • Session #{session} • {datetime.now().strftime('%B %d, %Y %I:%M %p')}</div>
            <div class="health">{health_emoji} App Health: {health_text}</div>
        </div>

        <!-- Circular Progress Ring -->
        <div class="ring-section">
            <div class="ring-container">
                <svg class="ring-svg" width="200" height="200">
                    <circle class="ring-bg" cx="100" cy="100" r="{ring_radius}"/>
                    <circle class="ring-progress" id="progressRing" cx="100" cy="100" r="{ring_radius}"/>
                </svg>
                <div class="ring-text">
                    <span class="ring-percent" id="ringPercent">0%</span>
                    <span class="ring-label">Pass Rate</span>
                </div>
            </div>
            <div class="ring-stats">
                <div class="ring-stat">
                    <div class="ring-stat-dot" style="background:#64b5f6;"></div>
                    <div class="ring-stat-info">
                        <span class="ring-stat-value">{total}</span>
                        <span class="ring-stat-label">Total Tests</span>
                    </div>
                </div>
                <div class="ring-stat">
                    <div class="ring-stat-dot" style="background:#00e676;"></div>
                    <div class="ring-stat-info">
                        <span class="ring-stat-value">{passed}</span>
                        <span class="ring-stat-label">Passed</span>
                    </div>
                </div>
                <div class="ring-stat">
                    <div class="ring-stat-dot" style="background:#ff1744;"></div>
                    <div class="ring-stat-info">
                        <span class="ring-stat-value">{failed}</span>
                        <span class="ring-stat-label">Failed</span>
                    </div>
                </div>
                <div class="ring-stat">
                    <div class="ring-stat-dot" style="background:#ce93d8;"></div>
                    <div class="ring-stat-info">
                        <span class="ring-stat-value">{session}</span>
                        <span class="ring-stat-label">Sessions</span>
                    </div>
                </div>
                <div class="ring-stat">
                    <div class="ring-stat-dot" style="background:#4fc3f7;"></div>
                    <div class="ring-stat-info">
                        <span class="ring-stat-value">{skills}</span>
                        <span class="ring-stat-label">Skills Learned</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Stats Cards with Glow -->
        <div class="stats-grid">
            <div class="stat-card glow-blue">
                <div class="stat-value stat-total">{total}</div>
                <div class="stat-label">Total Tests</div>
            </div>
            <div class="stat-card glow-green">
                <div class="stat-value stat-passed">{passed}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat-card glow-red">
                <div class="stat-value stat-failed">{failed}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card glow-gold">
                <div class="stat-value stat-rate">{pass_rate}%</div>
                <div class="stat-label">Pass Rate</div>
            </div>
            <div class="stat-card glow-purple">
                <div class="stat-value stat-session">{session}</div>
                <div class="stat-label">Sessions</div>
            </div>
            <div class="stat-card glow-cyan">
                <div class="stat-value stat-skills">{skills}</div>
                <div class="stat-label">Skills</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">📊 Pass / Fail Distribution</div>
                <canvas id="pieChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">📊 Category Breakdown</div>
                <canvas id="barChart"></canvas>
            </div>
        </div>

        <!-- Failed Tests -->
        <div class="section">
            <div class="section-title">❌ Failed Tests</div>
            {failed_section}
        </div>

        <!-- LLM Analysis with Typing Effect -->
        <div class="section">
            <div class="section-title">🧠 LLM Analysis <span class="llm-badge">GPT-5.2</span></div>
            <div class="llm-content" id="llmContent"><span class="llm-cursor" id="llmCursor"></span></div>
        </div>

        <!-- All Tests with Color-Coded Rows -->
        <div class="section">
            <div class="section-title">📋 All Test Results ({total} tests)</div>
            <div class="cat-legend">{cat_legend}</div>
            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterTests('ALL')">All ({total})</button>
                <button class="filter-btn" onclick="filterTests('PASS')">✅ Passed ({passed})</button>
                <button class="filter-btn" onclick="filterTests('FAIL')">❌ Failed ({failed})</button>
            </div>
            <table class="results-table">
                <thead>
                    <tr><th>ID</th><th>Test Name</th><th>Category</th><th>Status</th><th>Details</th></tr>
                </thead>
                <tbody>{all_rows}</tbody>
            </table>
        </div>

        <!-- Agent Memory -->
        <div class="section">
            <div class="section-title">🧠 Agent Memory</div>
            <h4 style="color:#4fc3f7; margin-bottom:12px;">🎯 Learned Skills ({skills})</h4>
            <div class="skills-container">{skills_list}</div>
            <h4 style="color:#64b5f6; margin: 20px 0 12px;">🔍 Working Selectors ({selectors})</h4>
            {selectors_html}
            <h4 style="color:#ce93d8; margin: 20px 0 12px;">🌐 Known Pages ({pages})</h4>
            {pages_html}
        </div>

        <!-- Footer -->
        <div class="footer">
            Generated by APA Testing Agent • Hermes-Inspired • Session #{session} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <script>
        // === CIRCULAR PROGRESS RING ANIMATION ===
        const ring = document.getElementById('progressRing');
        const ringPercent = document.getElementById('ringPercent');
        const targetRate = {pass_rate};
        const circumference = {ring_circumference};
        const targetOffset = {ring_offset};

        setTimeout(() => {{
            ring.style.strokeDashoffset = targetOffset;
            // Animate the percentage number
            let current = 0;
            const step = targetRate / 60;
            const counter = setInterval(() => {{
                current += step;
                if (current >= targetRate) {{
                    current = targetRate;
                    clearInterval(counter);
                }}
                ringPercent.textContent = Math.round(current) + '%';
            }}, 16);
        }}, 300);

        // === LLM TYPING EFFECT ===
        const llmText = {llm_escaped};
        const llmContainer = document.getElementById('llmContent');
        const llmCursor = document.getElementById('llmCursor');
        let charIndex = 0;

        function typeLLM() {{
            if (charIndex < llmText.length) {{
                const char = llmText[charIndex];
                if (char === '\\n') {{
                    llmContainer.insertBefore(document.createElement('br'), llmCursor);
                }} else {{
                    llmContainer.insertBefore(document.createTextNode(char), llmCursor);
                }}
                charIndex++;
                const delay = char === '.' ? 80 : char === '\\n' ? 60 : 12;
                setTimeout(typeLLM, delay);
            }} else {{
                llmCursor.style.display = 'none';
            }}
        }}

        // Start typing after 1.5s
        setTimeout(typeLLM, 1500);

        // === CHARTS ===
        new Chart(document.getElementById('pieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{passed}, {failed}, {skipped}],
                    backgroundColor: ['#00e676', '#ff1744', '#ffab00'],
                    borderWidth: 0,
                    hoverOffset: 8
                }}]
            }},
            options: {{
                responsive: true,
                cutout: '65%',
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{ color: '#ccc', padding: 16, font: {{ size: 12 }} }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(cat_labels)},
                datasets: [
                    {{
                        label: 'Passed',
                        data: {json.dumps(cat_pass)},
                        backgroundColor: 'rgba(0, 230, 118, 0.7)',
                        borderRadius: 4
                    }},
                    {{
                        label: 'Failed',
                        data: {json.dumps(cat_fail)},
                        backgroundColor: 'rgba(255, 23, 68, 0.7)',
                        borderRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        ticks: {{ color: '#8892b0', font: {{ size: 11 }} }},
                        grid: {{ display: false }}
                    }},
                    y: {{
                        ticks: {{ color: '#8892b0', stepSize: 2 }},
                        grid: {{ color: 'rgba(255,255,255,0.05)' }}
                    }}
                }},
                plugins: {{
                    legend: {{ labels: {{ color: '#ccc', font: {{ size: 12 }} }} }}
                }}
            }}
        }});

        // === FILTER ===
        function filterTests(status) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.test-row').forEach(row => {{
                if (status === 'ALL' || row.dataset.status === status) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""

        path = os.path.join(self.report_dir, "test_report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log(f"HTML report saved: {path}")
        log(f"Open in browser: {os.path.abspath(path)}")









# import json
# import os
# from datetime import datetime
# from utils.logger import log
# import config


# class Reporter:
#     def __init__(self, test_results, memory, page_map):
#         self.test_results = test_results
#         self.memory = memory
#         self.page_map = page_map
#         self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     def generate_all(self):
#         log("=" * 60)
#         log("GENERATING REPORTS")
#         log("=" * 60)

#         os.makedirs(config.REPORT_DIR, exist_ok=True)

#         self._generate_json()
#         self._generate_html()

#         log("All reports generated")

#     def _generate_json(self):
#         summary = self.memory.get_summary()
#         failed = [r for r in self.test_results if r["status"] == "FAIL"]

#         categories = {}
#         for r in self.test_results:
#             cat = r["category"]
#             if cat not in categories:
#                 categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
#             key = r["status"].lower()
#             categories[cat][key] = categories[cat].get(key, 0) + 1

#         report = {
#             "timestamp": self.timestamp,
#             "target_app": config.APP_URL,
#             "summary": summary,
#             "categories": categories,
#             "all_results": self.test_results,
#             "failed_details": failed,
#             "pages_discovered": len(self.page_map),
#             "memory_snapshot": {
#                 "sessions": self.memory.data["sessions"],
#                 "skills": len(self.memory.data["learned_skills"]),
#                 "known_pages": len(self.memory.data["known_pages"]),
#             }
#         }

#         path = f"{config.REPORT_DIR}/test_report.json"
#         with open(path, "w") as f:
#             json.dump(report, f, indent=2)
#         log(f"JSON report saved: {path}")

#     def _generate_html(self):
#         summary = self.memory.get_summary()
#         total = summary["total_tests"]
#         passed = summary["passed"]
#         failed = summary["failed"]
#         skipped = summary["skipped"]
#         pass_rate = summary["pass_rate"]

#         categories = {}
#         for r in self.test_results:
#             cat = r["category"]
#             if cat not in categories:
#                 categories[cat] = {"pass": 0, "fail": 0, "skip": 0}
#             key = r["status"].lower()
#             categories[cat][key] = categories[cat].get(key, 0) + 1

#         failed_tests = [r for r in self.test_results if r["status"] == "FAIL"]
#         passed_tests = [r for r in self.test_results if r["status"] == "PASS"]

#         cat_rows = ""
#         for cat, counts in categories.items():
#             cat_total = counts["pass"] + counts["fail"] + counts["skip"]
#             cat_rate = f"{(counts['pass'] / cat_total * 100):.0f}%" if cat_total > 0 else "0%"
#             cat_rows += f"""
#             <tr>
#                 <td>{cat}</td>
#                 <td>{cat_total}</td>
#                 <td class="pass">{counts['pass']}</td>
#                 <td class="fail">{counts['fail']}</td>
#                 <td>{counts['skip']}</td>
#                 <td>{cat_rate}</td>
#             </tr>"""

#         all_test_rows = ""
#         for r in self.test_results:
#             status_class = r["status"].lower()
#             icon = "&#9989;" if r["status"] == "PASS" else "&#10060;" if r["status"] == "FAIL" else "&#9197;"
#             all_test_rows += f"""
#             <tr class="{status_class}-row">
#                 <td>{r['id']}</td>
#                 <td>{r['category']}</td>
#                 <td>{r['name']}</td>
#                 <td class="{status_class}">{icon} {r['status']}</td>
#                 <td>{r['details']}</td>
#             </tr>"""

#         failed_rows = ""
#         for r in failed_tests:
#             failed_rows += f"""
#             <tr>
#                 <td>{r['id']}</td>
#                 <td>{r['name']}</td>
#                 <td>{r['details']}</td>
#             </tr>"""

#         skills_list = ""
#         for s in self.memory.data["learned_skills"][:10]:
#             skills_list += f"<li><strong>{s['name']}</strong> (used {s.get('times_used', 1)}x)</li>"

#         pages_list = ""
#         for p in self.page_map:
#             pages_list += f"""<li><strong>{p['page_name']}</strong> - {p['url']}
#                 <br>Buttons: {len(p['elements'].get('buttons', []))} |
#                 Forms: {p['elements'].get('forms', 0)} |
#                 Tables: {p['elements'].get('tables', 0)} |
#                 Inputs: {len(p['elements'].get('inputs', []))}</li>"""

#         bar_width_pass = (passed / total * 100) if total > 0 else 0
#         bar_width_fail = (failed / total * 100) if total > 0 else 0
#         bar_width_skip = (skipped / total * 100) if total > 0 else 0

#         html = f"""<!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>APA Testing Agent - Report</title>
#     <style>
#         * {{ margin: 0; padding: 0; box-sizing: border-box; }}
#         body {{
#             font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#             background: #0f0f23;
#             color: #e0e0e0;
#             padding: 20px;
#         }}
#         .container {{ max-width: 1200px; margin: 0 auto; }}

#         .header {{
#             background: linear-gradient(135deg, #1a1a3e, #2d2d6b);
#             padding: 30px;
#             border-radius: 12px;
#             margin-bottom: 20px;
#             border: 1px solid #3d3d8b;
#         }}
#         .header h1 {{
#             color: #7b8cff;
#             font-size: 28px;
#             margin-bottom: 5px;
#         }}
#         .header .subtitle {{
#             color: #9999cc;
#             font-size: 14px;
#         }}

#         .stats-grid {{
#             display: grid;
#             grid-template-columns: repeat(5, 1fr);
#             gap: 15px;
#             margin-bottom: 20px;
#         }}
#         .stat-card {{
#             background: #1a1a3e;
#             padding: 20px;
#             border-radius: 10px;
#             text-align: center;
#             border: 1px solid #2d2d6b;
#         }}
#         .stat-card .number {{
#             font-size: 36px;
#             font-weight: bold;
#         }}
#         .stat-card .label {{
#             font-size: 12px;
#             color: #9999cc;
#             margin-top: 5px;
#         }}
#         .stat-card.total .number {{ color: #7b8cff; }}
#         .stat-card.passed .number {{ color: #4caf50; }}
#         .stat-card.failed .number {{ color: #f44336; }}
#         .stat-card.skipped .number {{ color: #ff9800; }}
#         .stat-card.rate .number {{ color: #00bcd4; }}

#         .progress-bar {{
#             background: #1a1a3e;
#             border-radius: 10px;
#             padding: 20px;
#             margin-bottom: 20px;
#             border: 1px solid #2d2d6b;
#         }}
#         .progress-bar h3 {{ color: #7b8cff; margin-bottom: 10px; }}
#         .bar-container {{
#             height: 30px;
#             background: #2d2d4b;
#             border-radius: 15px;
#             overflow: hidden;
#             display: flex;
#         }}
#         .bar-pass {{ background: #4caf50; height: 100%; }}
#         .bar-fail {{ background: #f44336; height: 100%; }}
#         .bar-skip {{ background: #ff9800; height: 100%; }}

#         .section {{
#             background: #1a1a3e;
#             padding: 20px;
#             border-radius: 10px;
#             margin-bottom: 20px;
#             border: 1px solid #2d2d6b;
#         }}
#         .section h2 {{
#             color: #7b8cff;
#             margin-bottom: 15px;
#             font-size: 20px;
#         }}

#         table {{
#             width: 100%;
#             border-collapse: collapse;
#         }}
#         th {{
#             background: #2d2d6b;
#             color: #c0c0ff;
#             padding: 10px;
#             text-align: left;
#             font-size: 13px;
#         }}
#         td {{
#             padding: 10px;
#             border-bottom: 1px solid #2d2d4b;
#             font-size: 13px;
#         }}
#         .pass {{ color: #4caf50; font-weight: bold; }}
#         .fail {{ color: #f44336; font-weight: bold; }}
#         .skip {{ color: #ff9800; font-weight: bold; }}
#         .pass-row {{ background: rgba(76, 175, 80, 0.05); }}
#         .fail-row {{ background: rgba(244, 67, 54, 0.08); }}

#         .memory-section ul {{
#             list-style: none;
#             padding: 0;
#         }}
#         .memory-section li {{
#             padding: 8px 12px;
#             margin: 4px 0;
#             background: #2d2d4b;
#             border-radius: 6px;
#             font-size: 13px;
#         }}

#         .footer {{
#             text-align: center;
#             color: #666;
#             padding: 20px;
#             font-size: 12px;
#         }}
#     </style>
# </head>
# <body>
#     <div class="container">

#         <div class="header">
#             <h1>APA Testing Agent Report</h1>
#             <div class="subtitle">
#                 Hermes-Inspired Autonomous Testing | Session #{summary['session']}
#                 | {self.timestamp} | Target: {config.APP_URL}
#             </div>
#         </div>

#         <div class="stats-grid">
#             <div class="stat-card total">
#                 <div class="number">{total}</div>
#                 <div class="label">TOTAL TESTS</div>
#             </div>
#             <div class="stat-card passed">
#                 <div class="number">{passed}</div>
#                 <div class="label">PASSED</div>
#             </div>
#             <div class="stat-card failed">
#                 <div class="number">{failed}</div>
#                 <div class="label">FAILED</div>
#             </div>
#             <div class="stat-card skipped">
#                 <div class="number">{skipped}</div>
#                 <div class="label">SKIPPED</div>
#             </div>
#             <div class="stat-card rate">
#                 <div class="number">{pass_rate}</div>
#                 <div class="label">PASS RATE</div>
#             </div>
#         </div>

#         <div class="progress-bar">
#             <h3>Test Execution Progress</h3>
#             <div class="bar-container">
#                 <div class="bar-pass" style="width: {bar_width_pass}%"></div>
#                 <div class="bar-fail" style="width: {bar_width_fail}%"></div>
#                 <div class="bar-skip" style="width: {bar_width_skip}%"></div>
#             </div>
#             <div style="display:flex; gap:20px; margin-top:8px; font-size:12px;">
#                 <span><span style="color:#4caf50;">&#9632;</span> Passed {bar_width_pass:.0f}%</span>
#                 <span><span style="color:#f44336;">&#9632;</span> Failed {bar_width_fail:.0f}%</span>
#                 <span><span style="color:#ff9800;">&#9632;</span> Skipped {bar_width_skip:.0f}%</span>
#             </div>
#         </div>

#         <div class="section">
#             <h2>Category Breakdown</h2>
#             <table>
#                 <tr>
#                     <th>Category</th>
#                     <th>Total</th>
#                     <th>Passed</th>
#                     <th>Failed</th>
#                     <th>Skipped</th>
#                     <th>Pass Rate</th>
#                 </tr>
#                 {cat_rows}
#             </table>
#         </div>

#         <div class="section">
#             <h2>All Test Results</h2>
#             <table>
#                 <tr>
#                     <th>ID</th>
#                     <th>Category</th>
#                     <th>Test Name</th>
#                     <th>Status</th>
#                     <th>Details</th>
#                 </tr>
#                 {all_test_rows}
#             </table>
#         </div>

#         {"" if not failed_tests else f'''
#         <div class="section">
#             <h2>Failed Tests Detail</h2>
#             <table>
#                 <tr>
#                     <th>ID</th>
#                     <th>Test Name</th>
#                     <th>Failure Reason</th>
#                 </tr>
#                 {failed_rows}
#             </table>
#         </div>
#         '''}

#         <div class="section">
#             <h2>Pages Discovered ({len(self.page_map)})</h2>
#             <ul style="list-style:none; padding:0;">
#                 {pages_list}
#             </ul>
#         </div>

#         <div class="section memory-section">
#             <h2>Agent Memory</h2>
#             <p style="margin-bottom:10px; color:#9999cc;">
#                 Sessions: {self.memory.data['sessions']} |
#                 Skills: {len(self.memory.data['learned_skills'])} |
#                 Known Pages: {len(self.memory.data['known_pages'])} |
#                 Known Selectors: {len(self.memory.data['working_selectors'])}
#             </p>
#             <h3 style="color:#7b8cff; font-size:16px; margin:10px 0;">Learned Skills</h3>
#             <ul>{skills_list if skills_list else "<li>No skills learned yet</li>"}</ul>
#         </div>

#         <div class="footer">
#             APA Testing Agent | Hermes-Inspired | Powered by Playwright |
#             Generated: {self.timestamp}
#         </div>

#     </div>
# </body>
# </html>"""

#         path = f"{config.REPORT_DIR}/test_report.html"
#         with open(path, "w", encoding="utf-8") as f:
#             f.write(html)
#         log(f"HTML report saved: {path}")
#         log(f"Open in browser: {os.path.abspath(path)}")