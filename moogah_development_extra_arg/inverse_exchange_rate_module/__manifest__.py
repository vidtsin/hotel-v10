# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Inverse Exchange Rate",
    "version": "10.0.1.0.18",
    "depends": ['base', 'account', 'account_accountant'],
    "author": "BrowseInfo, Moogah",
    "description": """
    """,
    "website": "www.browseinfo.in",
    "data": [
        'security/security.xml',
        'views/currency_view.xml',
        'views/customer_invoice.xml',
        'views/account_payment_view.xml',
        'views/account_move_line_view.xml',
        'views/account_payment_group_view.xml',
        'views/sale_config_settings_views.xml',
        'views/purchase_res_config_views.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',

    ],
    'depends': ['vitt_sales_reports', 'sale_stock', 'purchase'],
    'qweb': [],
    "auto_install": False,
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
