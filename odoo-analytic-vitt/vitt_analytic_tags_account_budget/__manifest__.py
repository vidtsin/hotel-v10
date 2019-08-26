# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Account Budget',
    'summary': 'This module extend analytic_tag_dimension to Budgets Management',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'contributors': 'aguilar@bacgroup.net',
    'website': 'http://www.bacgroup.net',
    'category': 'Accounting',
    'description': """
        This module extend analytic_tag_dimension to Assets app Registers
    """,
    'depends': [
        'base',
        'account_budget',
        'vitt_analytic_tags_account',
    ],
    'data': [
        'views/account_budget_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
