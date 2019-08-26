# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################
{
    'name': 'VITT AGIP Web Service for Server',
    'description': 'VITT AGIP Web Service for Server',
    'summary': 'VITT AGIP Web Service. Este app solo debe ser instalado en el servidor donde se importarán los archivos del padrón AGIP.',
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'version': '10.0.1.1',
    'license': 'Other proprietary',
    'maintainer':'Osvaldo Gentile',
    'contributors':'',
    'category': 'Localization',
    'depends': ['account'],
    'data': [
        'views/views.xml',
        'data/ir_cron.xml'
    ],
}
