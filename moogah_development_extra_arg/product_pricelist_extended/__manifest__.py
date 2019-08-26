# -*- coding: utf-8 -*-
{
    'name': 'Product pricelists extended',
    'version': '10.0.1.0',
    'category': 'Hidden',
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'depends': ['base', 'purchase'],
    'description': """
    This module allows to add new fields in product, purchase order and pricelist models,
    and adds new options for 'base on' field  in price list item.
    """,
    'data': [
        'views/product_template_views.xml',
        'views/purchase_views.xml',
        'views/product_pricelist_views.xml',
        'wizard/transfer_cost_views.xml',
    ],
}
