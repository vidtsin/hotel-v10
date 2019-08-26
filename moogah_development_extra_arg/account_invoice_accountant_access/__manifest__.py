# -*- coding: utf-8 -*-

{
    'name': 'Account Invoice Accountant Access',
    'version': '1.0',
    'description': """
    This module adds a technical field on invoice model allowing to check if
    the user is accountant or supervisor.
    """,
    'author': 'Moogah',
    'summary': 'Allows to check if the user is accountant or supervisor',
    'depends': ['account'],
    'data': [
        'views/account_invoice_views.xml',
    ],
    'application': False,
}
