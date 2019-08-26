# -*- coding: utf-8 -*-

{
    'name': 'Envio de Facturas por Email',
    'version': '10.0.0.1.5',
    'author': 'Moogah',
    'website': 'https://www.moogah.com',
    'summary': 'Adds an action for sending several invoices by email at the same time',
    'depends': [
        'account',
        'account_invoice_accountant_access'
    ],
    'data': [
        'views/account_invoice_views.xml',
    ],
    'installable': True,
    'application': False,
}
