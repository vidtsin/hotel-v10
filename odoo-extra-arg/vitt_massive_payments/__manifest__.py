# -*- coding: utf-8 -*-
{
    'name': "Massive Payments",
    'summary': """Massive Payments""",
    'description': """This application adds the functionality to pay Supplier Invoices using Odoo's standard Payments.
    The invoices can be selected from the view list and by using the new Action 'Massive Payments' it allows the user to define 
    how much from each invoice he wants to paid. Once the operation is confirmed, the Payments are created and linked to the invoices .""",
    'author': "Moogah",
    'website': "http://www.moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.10',
    'depends': ['account'],
    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [],
    'application': True,
}