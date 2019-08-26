# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Sales',
    'summary': 'This module extend analytic_tag_dimension to Sales Registers',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Sales',
    'description': """
        This module extend analytic_tag_dimension to Sales app Registers
    """,
    'depends': [
        'sale',
        'vitt_analytic_tags_account',
    ],
    'data': [
        'views/sale.xml',
    ],
    'installable': True,
    'auto_install': False,
}
