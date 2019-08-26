# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags',
    'summary': 'This module extend analytic_tag_dimension',
    'version': '10.0.1.0.2',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Accounting',
    'description': """
        This module extend analytic_tag_dimension
    """,
    'depends': [
        'analytic',
        'analytic_tag_dimension',
    ],
    'data': [
        'views/analytic_view.xml',
        'views/account_view.xml',
        'views/settings_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
