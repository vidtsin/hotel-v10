# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################
{
    'name': 'VITT ARG EInvoice Format ',
    'description': 'Formato de impresión para Facturas Argentina',
    'summary': 'Este app instala el formato para Impresión de Facturas según requerimientos de Argentina',
    'author': 'Business Analytics Consulting Group S.A. de C.V.',
    'website': 'http://www.bacgroup.net',
    'version': '10.0.1.0.5',
    'license': 'Other proprietary',
    'maintainer': 'Salvatore Josue Trimarchi Pinto',
    'contributors': '',
    'category': 'Localization',
    'depends': [
        'account',
        'l10n_ar_afipws_fe',
        'account_document',
    ],
    'data': ['views/views.xml'],
}
