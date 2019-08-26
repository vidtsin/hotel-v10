# -*- coding: utf-8 -*-
{
    'name': "Subtipo para Diarios en Pagos/Recibos",

    'summary': """subtipo para diarios y pagos/recibos""",

    'description': """
        Este app agrega un campo de subtipo en los Diarios para permitir poder filtrar de forma más eficiente en los registros de Pagos y Recibos
    """,
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.1',
    'depends': ['account_payment_group','account',],
    'data': [
        'views/views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'application': True,
}