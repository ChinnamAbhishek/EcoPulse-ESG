{
    "name": "EcoPulse ESG",
    "version": "19.0.1.0.0",
    "summary": "Environmental, Social and Governance Management Platform",
    "category": "Operations",
    "author": "Abhishek Chinnam",
    "license": "LGPL-3",

    "depends": [
        "base",
        "web",
        "mail",
        "hr",
        "product",
    ],

    "data": [
    "security/ecopulse_security.xml",
    "security/ir.model.access.csv",

    "data/sequence_data.xml",

    "views/dashboard_action.xml",
    "views/department_views.xml",
    "views/emission_factor_views.xml",
    "views/carbon_transaction_views.xml",
    "views/environmental_goal_views.xml",

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

    "application": True,
    "installable": True,
    "auto_install": False,
}