# -*- coding: utf-8 -*-
{
    'name': "Deshabilitar registrar Pagos desde Facturas",
    'summary': """Deshabilitar registrar Pagos desde Facturas""",
    'description': """Este app deshabilita la opción que permite realizar Pagos desde los registros de Facturas de Clientes y Proveedores.
    Al instalarlo, el botón Registrar Pago ya no es visible para el usuario.""",
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    'category': 'Uncategorized',
    'version': '10.0.1.0.1',
    'depends': ['sale','purchase'],
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'application': True,
}