# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 BACG S.A. de C.V. (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': 'VITT - Analytic Tags - Payroll',
    'summary': 'This module extend analytic_tag_dimension to Payroll Accounting Register',
    'version': '10.0.1.0',
    "author": "Business Analytics Consulting Group S.A. de C.V.",
    'website': 'http://www.bacgroup.net',
    'category': 'Accounting',
    'description': """
        This module extend analytic_tag_dimension to Payroll Accounting Register
    """,
    'depends': [
        'hr_payroll_account',
        'vitt_analytic_tags',
    ],
    'data': [
        'views/hr_analytic_tags.xml',
    ],
    'installable': True,
    'auto_install': False,
}
