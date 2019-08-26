# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Chart of Accounts Template',
    'version': '10.0.1.1',
    'description': """
Argentinian chart of accounts and tax codes, template.
==================================================

Plan contable argentino e impuestos de acuerdo a disposiciones vigentes

    """,
    'author': ['Moogah'],
    'website': 'http://www.moogah.com',
    'category': 'Localization',
    'depends': ['base', 'account'],
    'data':[
        'data/l10n_ar_chart_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.yml',
        'data/check_accounts_data.xml'
    ],
}
#<div>Icons made by <a href="https://www.flaticon.com/authors/twitter" title="Twitter">Twitter</a> from <a href="https://www.flaticon.com/" 		    title="Flaticon">www.flaticon.com</a> is licensed by <a href="http://creativecommons.org/licenses/by/3.0/" 		    title="Creative Commons BY 3.0" target="_blank">CC 3.0 BY</a></div>