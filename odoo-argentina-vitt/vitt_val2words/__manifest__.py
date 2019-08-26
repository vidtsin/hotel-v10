# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

{
    'name': "VITT Numbers to Words",
    'description': """
    Add Feature to Convert Numbers to Words \n
    Configure; \n
    - Accounting>>Settings>>Values in words
    - Accounting>>Settings>>Settings>>Company Settings; Set Default Language to convert Numbers to words
    """,
    'summary': 'Convert Numbers to Words',
    'author': 'Business Analytics Consulting Group S.A. de C.V.',
    'website': 'www.bacgroup.net',
    'version': '10.0.1.1',
    'license': 'Other proprietary',
    'maintainer': '',
    'contributors': '',
    'category': 'Extra Tools',



    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'web'],

    # 'external_dependencies': {'python': ['num2words']},

    # always loaded
    'data': [
        'data/vals2words_es.xml',
        'data/vals2words_en.xml',
        'views/res_company_views.xml',
        'views/settings_view.xml',
        'views/view.xml',
        'security/ir.model.access.csv',
    ],

    'js': [
        'static/src/js/val2text.js'
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
