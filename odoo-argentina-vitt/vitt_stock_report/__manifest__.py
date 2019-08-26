# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################
{
    'name': 'Nuevo Remito de Entrega',
    'description': 'El app habilita un nuevo formato de Remito de Entrega desde el menú de Impresión. Incluye la columna de Cantidad Ordenada y la firma.',
    'summary': 'Nuevo Remito de Entrega',
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'version': '10.0.1.1',
    'license': 'Other proprietary',
    'maintainer': 'Osvaldo Jorge Gentile',
    'contributors': '',
    'category': 'Localization',
    'depends': ['stock'],
    'data': [
        'views/report_deliveryslip.xml',
        'views/views.xml',
    ],
}
