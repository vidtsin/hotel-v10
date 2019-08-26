# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################

{
    "name": "POS PayuLatam Payment",
    "version": "10.0.0.1",
    "category": "Point of Sale",
    "depends": ['payment', 'payment_payulatam_bi', 'point_of_sale'],
    'summary': 'POS PayuLatam Payment Acquires',
    "description": """ POS PayuLatam Payment Acquire """,
    "data": [
        'views/custom_sale_view.xml',
        'views/custom_pos_view.xml',
    ],
    'qweb': ['static/src/xml/pos_extended.xml'],
    "auto_install": False,
    "installable": True,
    #"images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
