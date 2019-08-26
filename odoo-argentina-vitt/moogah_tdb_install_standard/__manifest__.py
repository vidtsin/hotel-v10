# -*- coding: utf-8 -*-
{
    'name': "Moogah Setup Standard Modules", 

    'summary': """Instalación automática de módulos base estándar""",

    'description': """
        Instala de forma automática todos los siguientes módulos: Contabilidad, Compras, Inventarios, Ventas, CRM, Empleados, Gastos, Calendario y Tablero
        """,

    'author': "Moogah",
    'website': "http://www.moogah.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '10.0.1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'account_accountant',
        'sale',
        'purchase',
        'crm',
        'hr',
        'hr_expense',
        'account_cancel',
        'contacts',
        'calendar',        
        'board'        
     ],
    # always loaded
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}