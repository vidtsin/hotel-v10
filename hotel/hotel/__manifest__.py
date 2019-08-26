# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Management',
    'summary': 'Manage Hotel room and booking management system',
    'version': '10.0.1.0.4',
    'description': '''This module helps customer to book their room into the
    the Hotel''',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'category': 'Generic Modules/Hotel Management',
    'license': 'AGPL-3',
    'depends': ['sale_stock', 'point_of_sale', 'report', 'web_timepicker_widget'],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_sequence.xml',
        'data/hotel_data.xml',
#        'data/cron_job.xml',
        'wizard/change_room_qty_views.xml',
        'report/hotel_report.xml',
        'report/report_hotel_management.xml',
        'views/res_company.xml',
        'views/hotel_view.xml',
        'views/res_partner_view.xml',
        'wizard/hotel_wizard.xml',
        'views/room_move.xml',
    ],
    'demo': ['data/hotel_demo_data.xml'],
    'css': ['static/src/css/room_kanban.css'],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
    'external_dependencies': {
        'python': ['forex_python'],
    },
}
