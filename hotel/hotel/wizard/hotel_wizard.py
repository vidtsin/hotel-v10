# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FolioReportWizard(models.TransientModel):
    _name = 'folio.report.wizard'
    _rec_name = 'date_start'

    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')

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
    def print_report(self):
        
        data = {
            'ids': self.ids,
            'model': 'hotel.folio',
            'form': self.read(['date_start', 'date_end'])[0]
        }
        return self.env['report']. \
            get_action(self, 'hotel.report_hotel_folio', data=data)
