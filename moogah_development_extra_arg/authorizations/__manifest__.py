# -*- coding: utf-8 -*-

{
    'name': 'Authorizations',
    'version': '10.0.1.0',
    'category': 'Tools',
    'description': """
    This module allows users to manage purchases, sales and invoices approvals, based on the transaction's total amount.
    """,
    'author': 'Moogah',
    'website': 'www.moogah.com',
    'summary': 'Approval process of purchases, sales and invoices.',
    'depends': ['account_accountant', 'sale', 'purchase', 'l10n_ar_afipws_fe'],
    'data': [
        'views/sale_views.xml',
        'views/purchase_views.xml',
        'views/account_invoice_view.xml',
        'views/res_config_view.xml'
    ],
    'installable': True,
}
