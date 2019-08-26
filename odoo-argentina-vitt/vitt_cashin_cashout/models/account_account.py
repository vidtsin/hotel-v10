from odoo import models, api, fields, _

class AccountAccount(models.Model):
    _inherit = "account.account"

    wtaxf = fields.Selection(selection_add=[('cashin_out', 'Entrada/Salida de Caja')], string='Used For')
