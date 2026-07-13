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
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/environmental_views.xml",
        "views/department_views.xml",
        "views/dashboard_action.xml",
        "views/menu_views.xml",
        "data/demo_data.xml",
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