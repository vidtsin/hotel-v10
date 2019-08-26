# -*- coding: utf-8 -*-
{
    'name': 'Control CUIT Duplicados',
    'summary': 'Control para evitar la duplicación de CUIT/CUIL',
    'description': """Este app incluye un campo adicional en la Configuración del módulo de Contabilidad que permite especificar el Tipo de Documento sobre el que se realizará el control.
    """,
    'version': '10.0.1.0.5',
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'depends': [
        'l10n_ar_account_withholding',
        'vitt_nl_setting',
        'account',
    ],
    'data': [
        'views/views.xml',
    ],
    'installable': True,
}
