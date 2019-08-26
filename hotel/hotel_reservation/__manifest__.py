# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Hotel Reservation Management',
    'version': '10.0.1.0.1',
    'author': 'Odoo Community Association (OCA), Serpent Consulting \
                Services Pvt. Ltd., Odoo S.A.',
    'category': 'Generic Modules/Hotel Reservation',
    'license': 'AGPL-3',
    'depends': ['hotel', 'stock', 'mail'],
    'demo': ['data/hotel_reservation_data.xml'],
    'data': [
        'data/booking_reminder_scheduler.xml',
        'data/reminder_email_template.xml',
        'data/hotel_reservation_sequence.xml',
        'security/ir.model.access.csv',
        'wizard/folio_room_allocation_wizard.xml',
        'wizard/hotel_reservation_wizard.xml',
        'wizard/reservation_cancel_wizard_view.xml',
        'report/reservation_receipt_template.xml',
        'report/reservation_checkin_template.xml',
        'report/reservation_checkout_template.xml',
        'report/reservation_room_template.xml',
        'report/reservation_max_room_template.xml',
        'report/report_view.xml',
        'views/res_company_view.xml',
        'views/hotel_reservation_view.xml',
        'views/email_temp_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
