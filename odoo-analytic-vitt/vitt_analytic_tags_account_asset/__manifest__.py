# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Account Assets',
    'summary': 'This module extend analytic_tag_dimension to Assets Registers',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Accounting',
    'description': """
        This module extend analytic_tag_dimension to Assets app Registers
    """,
    'depends': [
        'account_asset',
        'vitt_analytic_tags_account',
    ],
    'data': [
        'views/account_asset.xml',
    ],
    'installable': True,
    'auto_install': False,
}
