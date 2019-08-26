# -*- coding: utf-8 -*-
{
    'name': "Extension a Customer/Supplier Outstanding Statement",
    'summary': """Este app extiende las funcionalidades del informe""",
    'description': """Customer/Supplier Outstanding Statement Extended""",
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.2',
    'depends': [
        'customer_outstanding_statement',
        'account',
    ],
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'application': True,
}
