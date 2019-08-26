# -*- coding: utf-8 -*-
# delivery_extended module for Odoo v10
{
    'name': 'Calendar Working Hours',
    'description': """
        This module adds calendar modification for working hours only
    """,
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'category': 'Other',
    'version': '1.0',
    'summary': 'This module adds calendar modification for working hours only',
    'depends': ['web_calendar'],
    'data': [
        'views/template.xml'
    ],
    'application': False,
}
