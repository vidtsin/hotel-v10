# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Purchases',
    'summary': 'This module extend analytic_tag_dimension to Purchases Registers',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Purchases',
    'description': """
        This module extend analytic_tag_dimension to Purchases app Registers
    """,
    'depends': [
        'purchase',
        'vitt_analytic_tags_account',
    ],
    'data': [
        'views/purchase.xml',
    ],
    'installable': True,
    'auto_install': False,
}
