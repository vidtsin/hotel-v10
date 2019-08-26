# -*- coding: utf-8 -*-
{
    'author': "Moogah,Moldeo Interactive,ADHOC SA",
    'category': 'Localization/Argentina',
    'depends': [
        'partner_identification',
    ],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Tipos de Documentos Argentina',
    'data': [
        'data/res_partner_id_category_data.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_id_category_view.xml',
        'views/res_partner_id_number_view.xml',
    ],
    'version': '10.0.1.0.3',
    'post_init_hook': 'post_init_hook',
}
