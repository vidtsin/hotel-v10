# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from lxml import etree
import calendar
from datetime import timedelta, datetime


class PartnerTransactionReportWizard(models.TransientModel):
    _name = 'partner.transaction.report.wizard'
    _description = 'Wizard that show the partners transactions report'

    initial_date = fields.Date('Date From', default=lambda s: datetime.today().replace(day=1), required=True)
    end_date = fields.Date('Date To', default=lambda s: datetime.today().replace(day=1).replace(
        day=calendar.monthrange(datetime.today().year, datetime.today().month)[1]), required=True)
    partner_ids = fields.Many2many('res.partner', string='Partners',  required=True)
    type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')], default='customer', string='Type')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(PartnerTransactionReportWizard, self).fields_view_get(view_id=view_id,
                                                                          view_type=view_type,
                                                                          toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.get('default_type', False) and view_type == 'form':
            type = self._context.get('default_type', False)
            for node in doc.xpath("//field[@name='partner_ids']"):
                if type == 'customer':
                    node.set('domain', "[('customer', '=', True)]")
                else:
                    node.set('domain', "[('supplier', '=', True)]")
            res['arch'] = etree.tostring(doc)
        return res
