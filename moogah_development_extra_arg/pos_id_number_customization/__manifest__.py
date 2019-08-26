# -*- coding: utf-8 -*-
{
    'name': "POS Busqueda de Cliente por Id. Tributario",
    'summary': """POS Busqueda de Cliente por Id. Tributario""",
    'description': """
    This module allows the search of customers by Main Identification Number.
    """,
    'author': "Moogah",
    'website': "www.moogah.com",
    'category': 'Point of Sale',
    'version': '10.0.1.1',
    'depends': ['l10n_ar_partner', 'point_of_sale'],
    'qweb': [
    ],
    'data': [
        'views/pos_id_number_customization_view.xml',
    ],
    'demo': [],
    'installable': True,
}
