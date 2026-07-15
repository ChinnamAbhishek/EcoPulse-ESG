# -*- coding: utf-8 -*-

{
    "name": "EcoPulse ESG",

    "version": "19.0.1.0.0",

    "summary": (
        "Environmental Sustainability and Carbon Emission "
        "Management Platform"
    ),

    "description": """
EcoPulse ESG
============

EcoPulse ESG is an Odoo-based environmental sustainability
management platform.

Main Features
-------------
* Carbon transaction management
* Emission-factor configuration
* Scope 1, Scope 2 and Scope 3 tracking
* Environmental-goal management
* Department-level ESG monitoring
* Interactive sustainability dashboard
* Date, department, scope and status filters
* Carbon transaction CSV export
* Professional ESG PDF report generation
* Monthly emission analysis
* Department emission ranking
* Emission source analysis
* Goal progress and risk monitoring
    """,

    "category": "Operations/Environmental Sustainability",

    "author": "EcoPulse ESG Team",

    "website": "https://github.com/ChinnamAbhishek/EcoPulse-ESG",

    "license": "LGPL-3",

    "depends": [
        "base",
        "web",
        "mail",
        "hr",
    ],
"data": [
    "security/security.xml",
    "security/ir.model.access.csv",
    "data/sequence_data.xml",
    "views/dashboard_action.xml",
    "views/department_views.xml",
    "views/environmental_views.xml",
    "views/carbon_trust_score_views.xml",
    "views/carbon_reduction_simulator_views.xml",
    "views/carbon_budget_views.xml",
    "views/esg_report_wizard_views.xml",
    "report/esg_summary_report.xml",
    "views/menu_views.xml",
],
 

    "assets": {
        "web.assets_backend": [
            "ecopulse_esg/static/src/dashboard/dashboard.js",
            "ecopulse_esg/static/src/dashboard/dashboard.xml",
            "ecopulse_esg/static/src/dashboard/dashboard.scss",
        ],
    },

    "images": [
        "static/description/icon.png",
    ],

    "installable": True,

    "application": True,

    "auto_install": False,
}