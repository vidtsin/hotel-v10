# -*- coding: utf-8 -*-
{
    'name': "Términos de Pago - Pagos Contado",
    'summary': """Este app vincula una cuenta contable al Término de Pago.""",
    'description': """
        El app agrega un nuevo campo para especificar una cuenta (de tipo Banco o Caja) para que la factura sea registrada contra este cuenta en lugar de usar la Cuenta de Deudores.
        Al validarse, la factura quedará marcada como totalmente pagada.
    """,
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.4',
    'depends': [
        'account',
     ],
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'application': True,
}