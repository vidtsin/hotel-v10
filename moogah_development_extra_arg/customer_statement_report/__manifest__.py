# -*- coding: utf-8 -*-
{
    "name": "Customer Statement Report",
    'category': 'Localization/Argentina',
    'version': '10.0.1.0.1',
    'author': 'Moogah',
    'website': 'www.moogah.com',
    'summary': 'Customization of Customer Statement Report',
    'description': """Customer Statement Report
    """,
    'depends': [
        'account_reports', 'l10n_ar_account'
    ],
    'data': [
        'views/res_partner_view.xml',
        'views/report_followup.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
