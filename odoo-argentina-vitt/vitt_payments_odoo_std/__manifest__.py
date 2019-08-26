# -*- coding: utf-8 -*-
{
    'name': "Pagos & Recibos Standard Odoo",
    'summary': """Acces a Pagos & Recibos standard de Odoo""",
    'description': """Permite acceder al menú para ver los Pagos de Odoo cuando se tiene instalado el app de Pagos en Grupo""",
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.4',
    'depends': [
        'account_accountant',
        'account_payment_group_document',
        'account_payment_group'
    ],
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'application': True,
}