# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HotelReservationWizard(models.TransientModel):
    _name = 'hotel.reservation.wizard'

    date_start = fields.Date('Start Date', required=True)
    date_end = fields.Date('End Date', required=True)

    @api.constrains('date_start', 'date_end')
    def check_start_end_date(self):
        """
        When enddate should be greater than the startdate.
        """
        if self.date_end and self.date_start:
            if self.date_end < self.date_start:
                raise ValidationError(_('End Date should be greater \
                                         than Start Date.'))
    @api.multi
    def report_reservation_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env['report'
                        ].get_action(self,
                                     'hotel_reservation.reservation_room_report_template',
                                     data=data)

    @api.multi
    def report_checkin_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0],
        }
        return self.env['report'
                        ].get_action(self,
                                     'hotel_reservation.reservation_checkin_report_template',
                                     data=data)

    @api.multi
    def report_checkout_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env['report'
                        ].get_action(self,
                                     'hotel_reservation.reservation_checkout_report_template',
                                     data=data)

    @api.multi
    def report_maxroom_detail(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.reservation',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env['report'
                        ].get_action(self,
                                     'hotel_reservation.reservation_maxroom_report_template',
                                     data=data)
