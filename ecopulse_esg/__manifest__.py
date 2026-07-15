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
        # Security groups
        "security/security.xml",

        # Access rights
        "security/ir.model.access.csv",

        # Initial sequence
        "data/sequence_data.xml",

        # Dashboard action
        "views/dashboard_action.xml",

        # Department views
        "views/department_views.xml",

        # Combined environmental views
        "views/environmental_views.xml",

        # ESG report wizard
        "views/esg_report_wizard_views.xml",

        # ESG PDF report
        "report/esg_summary_report.xml",

        # Menus
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