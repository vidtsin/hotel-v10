from odoo import http, models, fields, api, _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    region_tax_control_id = fields.Many2one(
        'res.country.state',
        string='Region Tax Control',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        self.region_tax_control_id = self.partner_shipping_id.state_id
