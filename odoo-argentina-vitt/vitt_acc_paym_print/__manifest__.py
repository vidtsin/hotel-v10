# -*- coding: utf-8 -*-
{
    'name': "Formato de Impresion para Pagos y Recibos",

    'summary': """Localizacion Argentina, impresion de Pagos a Proveedores y Recibos de Clientes""",

    'description': """
        Este app instala el formato de impresión para los registros de pagos en grupo para Pagos a Proveedores y Recibos de Clientes
    """,
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.1',
    'depends': [
        'account_payment_group',
        'account_check',
        'vitt_val2words',
    ],
    'data': [
        #'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'demo': [],
    'application': True,
}