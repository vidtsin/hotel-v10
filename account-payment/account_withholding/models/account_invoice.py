# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, Warning


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    state_id = fields.Many2one(
        'res.country.state',
        string="State",
        states={'paid': [('readonly', True)]},
    )

    @api.onchange('partner_id')
    def onchange_partner_id_new(self):
        self.state_id = self.partner_id.state_id

    @api.multi
    def write(self,vals):
        for rec in self:
            if rec.origin:
                if len(rec.origin.split()) == 1:
                    po = rec.env['purchase.order'].search([('name', '=', rec.origin)])
                    if po:
                        vals['state_id'] = po.state_id.id
                    if not 'state_id' in vals.keys():
                        vals['state_id'] = rec.partner_id.state_id.id
                else:
                    vals['state_id'] = rec.partner_id.state_id.id

        return super(AccountInvoice, self).write(vals)
