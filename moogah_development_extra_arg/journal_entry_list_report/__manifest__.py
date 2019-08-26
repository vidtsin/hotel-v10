# -*- coding: utf-8 -*-

{
    'name': 'Journal Entry List Report',
    'version': '10.0.1.2',
    'category': 'Accounting',
    'summary': '',
    'description': """
    
    Journal Entry List Report
""",
    'author': 'Moogah',
    'website': 'www.moogah.com',
    'images': [],
    'depends': ['account_accountant', 'l10n_ar_account', 'inverse_exchange_rate_module',
                'detailed_general_ledger_report', 'account_origin_document'],
    'data': [
        'views/report_financial.xml',
        'views/journal_entry_list_report_view.xml',
        'wizard/journal_entry_list_report_wizard_views.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
