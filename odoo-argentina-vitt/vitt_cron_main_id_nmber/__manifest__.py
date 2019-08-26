# -*- coding: utf-8 -*-
{
    'name': "vitt cron main id number",

    'summary': """vitt cron main id number""",

    'description': """
        vitt cron main id number
    """,

    'author': "Moogah",
    'website': "http://www.Moogah.com",

    'category': 'Uncategorized',
    'version': '10.0.1.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
     ],

    # always loaded
    'data': [
        'views/template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}