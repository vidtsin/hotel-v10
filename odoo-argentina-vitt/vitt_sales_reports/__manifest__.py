# -*- coding: utf-8 -*-
{
    'name': "Configuracion, Informes y Exportaciones Impositivas para ARG",
    'summary': """Configuracion, Informes y Exportaciones Impositivas para ARG""",
    'description': """
        Configuración y campos adicionales para el manejo de impuestos de ARG, Exportaciones e Informes.
    """,
    'author': "Moogah",
    'website': "http://www.Moogah.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '10.0.1.1.11',
    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'account',
        'l10n_ar_account',
        'account_withholding_automatic',
        'account_withholding',
        'vitt_nl_setting',
    ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/account_tax.xml',
        'views/templates.xml',
        'views/sicore_view.xml',
        'views/citi_setting_views.xml',
        'data/sicore_region_codes_data.xml',
        'data/sicore_tax_codes_data.xml'
    ],
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}