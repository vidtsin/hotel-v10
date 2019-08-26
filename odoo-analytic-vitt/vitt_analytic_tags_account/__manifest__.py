# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Account',
    'summary': 'This module extend analytic_tag_dimension to Accounting Registers',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Accounting',
    'description': """
        This module extend analytic_tag_dimension to Accounting Registers
    """,
    'depends': [
        'account',
        'vitt_analytic_tags',
    ],
    'data': [
        'views/account_view.xml',
        'views/partner_view.xml',
        'views/product_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
