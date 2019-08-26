# -*- coding: utf-8 -*-

{
    'name': 'Partner Transaction Report',
    'version': '10.0.0.1',
    'category': 'Accounting',
    'summary': '',
    'description': """
    
    Partner Transaction Report
""",
    'author': 'Moogah',
    'website': 'https://www.moogah.com/',
    'images': [],
    'depends': ['account', 'account_accountant', 'account_payment_group_document', 'l10n_ar_account',
                'inverse_exchange_rate_module'],
    'qweb': [
        'static/src/xml/templates.xml'
    ],
    'data': [
        'views/account_payment_view.xml',
        'views/bi_partner_transaction_report_view.xml',
        'static/src/xml/download_file_widget_templates.xml',
        'wizard/partner_transaction_report_wizard_view.xml',
        'views/bi_partner_transaction_report_template.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
