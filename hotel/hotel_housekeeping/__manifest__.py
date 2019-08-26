# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Housekeeping Management',
    'version': '10.0.1.0.1',
    'author': 'Odoo Community Association (OCA),\
                Serpent Consulting Services Pvt. Ltd., Odoo S.A.',
    'website': 'http://www.serpentcs.com',
    'license': 'AGPL-3',
    'category': 'Generic Modules/Hotel Housekeeping',
    'depends': ['hotel', 'hr'],
    'demo': ['data/hotel_housekeeping_data.xml', ],
    'data': [
        # 'report/hotel_housekeeping_report.xml',
        # 'report/activity_detail.xml',
        # 'wizard/hotel_housekeeping_wizard.xml',
        'security/ir.model.access.csv',
        'views/hotel_housekeeping_view.xml',
        'views/hotel_housekeeper_view.xml'
    ],
    'installable': True,
}
