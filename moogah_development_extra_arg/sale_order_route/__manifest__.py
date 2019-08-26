# -*- coding: utf-8 -*-
# sale_order_route module for Odoo v10
{
    'name': 'Sale Order Routes',
    'summary': 'Inventory routes management in Sale Orders',
    'description': """
    This module expedites SO lines' filling in companies that manage different Inventory Routes.
    """,
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'category': 'Sales',
    'version': '10.0.1.0',
    'depends': ['sale_stock'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'application': False,
}
