# -*- coding: utf-8 -*-
{
    "name": "Factura Electrónica Argentina Mercosur/mipymes",
    'version': '10.0.1.0.13',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'Moogah',
    'license': 'AGPL-3',
    'summary': 'WS Bonos Fiscales/MiPymes Electronicos AFIP',
    'depends': [
        'l10n_ar_afipws',
        'l10n_ar_account',
        'l10n_ar_afipws_fe',
        'account_document',
    ],
    'data': ['views/views.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
