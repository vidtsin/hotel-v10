# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Management Dashboard',
    'version': '10.0.1.0.0',
    'description': '''This module is for the HMS Dashboard. ''',
    'author': '''Serpent Consulting Services Pvt. Ltd.''',
    'website': 'http://www.serpentcs.com',
    'category': 'Hotel Management',
    'license': "AGPL-3",
    'complexity': 'easy',
    'Summary': 'A Module For Hotel Management Dashboard',
    'depends': [
        'hotel', 'web', 'hotel_reservation',
        'account', 'hotel_room_availability'],
    'data': [
        'security/ir.model.access.csv',
        'views/template_view.xml',
        'views/dashboard_view.xml',
    ],
    'qweb': [
        "static/src/xml/hms_dashboard.xml",
    ],
    'installable': True,
    'application': True
}
