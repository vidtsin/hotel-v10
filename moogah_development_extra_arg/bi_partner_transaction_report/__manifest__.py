# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##################################################################################
{
    'name': 'Partner Transaction Report',
    'version': '10.0.0.5',
    'category': 'Accounting',
    'summary': '',
    'description': """
    
    Partner Transaction Report
""",
    'author': 'BrowseInfo',
    'website': 'http://www.browseinfo.in',
    'images': [],
    'depends': ['account','account_accountant','account_reports','account_payment_group','l10n_ar_account','inverse_exchange_rate_module'],
    'qweb': [
        'static/src/xml/qweb.xml',
    ],
    'data': [
        'views/bi_partner_transaction_extended_view.xml',
        'views/report_financial.xml',
        'views/bi_partner_transaction_report_view.xml',
        'views/bi_vendor_transaction_report_view.xml',
        'views/currencies_partner_ledger_report_view.xml',
        'views/res_partner_view.xml',
        'views/account_payment_view.xml',
        'wizard/partner_transaction_report_wizard_views.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
