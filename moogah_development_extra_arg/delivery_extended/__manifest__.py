# -*- coding: utf-8 -*-
# delivery_extended module for Odoo v10
{
    'name': 'Delivery Extended',
    'description': """
        This module adds freight information in Sale and Delivery orders
    """,
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'category': 'Other',
    'version': '10.0.1.0.5',
    'summary': 'Freight information in Sale and Delivery orders',
    'depends': ['sale_order_dates', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/freight_view.xml',
        'views/sale_order_view.xml',
        'views/stock_picking_view.xml',
        'views/res_partner_view.xml'
    ],
    'application': False,
}
