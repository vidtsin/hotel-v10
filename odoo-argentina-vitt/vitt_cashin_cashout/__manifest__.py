# -*- coding: utf-8 -*-
{
    'name': "Entradas y Salidas de caja",
    'summary': """Modulo Caja""",
    'description': """
        Modulo de Entradas y Salidas de Caja
    """,
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.13',
    'depends': [
        'account',
        'account_payment_fix',
        'account_check',
        'account_withholding',
        'hr',
        'vitt_account_subtype',
        'vitt_analytic_tags',
     ],
    'data': [
        'data/sequence.xml',
        'views/cash_view.xml',
        'views/res_partner.xml',
        'wizard/change_check_wizard_views.xml',
        'security/ir.model.access.csv',
        'views/template.xml',
    ],
    'demo': [],
    'application': True,
}