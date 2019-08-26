# -*- coding: utf-8 -*-
{
    "name": "Partners Invoices Journals",
    'category': 'Localization/Argentina',
    'version': '10.0.1.1.10',
    'author': 'Moogah',
    'website': 'www.moogah.com',
    'summary': 'Partners Invoices Journals',
    'description': """Partners Invoices Journals""",
    'depends': [
        'account',
        'receipt_and_payment_journal_report',
    ],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
