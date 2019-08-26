# -*- coding: utf-8 -*-

{
    "name": "Detailed General Ledger Report",
    'summary': "Detailed version of the General Ledger with analytic tags filter support",
    "version": "10.0.1.9",
    "license": "AGPL-3",
    "author": "Moogah",
    "website": "",
    "depends": [
        'vitt_analytic_tags',
        'account_reports',
        'account_document'
    ],
    "data": [
        'data/detailed_general_ledger_data.xml',
        'views/account_general_ledger_report_menu.xml',
        'views/report_financial.xml',
    ],
    "qweb": [
            'static/src/xml/account_report_backend.xml',
        ],
    "demo": []
}
