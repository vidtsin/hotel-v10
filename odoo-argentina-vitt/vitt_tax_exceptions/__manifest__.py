# -*- coding: utf-8 -*-
{
    'name': 'Retenciones y Percepciones v2',
    'description': 'Nuevo código para Retenciones y Percepciones',
    'summary': 'OBS este app instala el nuevo código de Retenciones y Percepciones',
    'author': 'Moogah',
    'website': 'www.moogah.com',
    'category': 'Accounting & Finance',
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_exceptions.xml',
        'views/tax_exceptions.xml',
    ],
    'depends': [
        'l10n_ar_account_withholding',
    ],
    'installable': True,
    'test': [],
    'version': '10.0.1.0.4',
}
