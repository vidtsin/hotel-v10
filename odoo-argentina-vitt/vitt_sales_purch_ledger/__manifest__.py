# -*- coding: utf-8 -*-
{
    'name': "Informes de Cuentas x Cobrar y Cuentas x Pagar",

    'summary': """Informes de Cuentas x Cobrar y Cuentas x Pagar""",

    'description': """
        Informes de Cuentas x Cobrar y Cuentas x Pagar con soporte de Pagos en Grupo (WIP)
    """,

    'author': "Moogah",
    'website': "http://www.Moogah.com",

    'category': 'Uncategorized',
    'version': '10.0.1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
     ],

    # always loaded
    'data': [
        'views/views.xml',
        'views/templates.xml',
        'views/templatessl.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}