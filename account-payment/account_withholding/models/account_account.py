from odoo import models, api, fields, _
from openerp.exceptions import ValidationError

class LogAccountAccount(models.Model):
    _name = "log.account.account"

    user = fields.Char("Usuario",size=30)
    wh_codes = fields.Char("Codigos de Retencion")
    acc_name =  fields.Char("Usuario",size=130)

class AccountAccount(models.Model):
    _inherit = "account.account"

    wtax_ids = fields.Many2many('account.tax', 'ab3_rel',
        'a3_id', 'b3_id', string='Withholding Taxes',domain=['|',('type_tax_use', '=', 'supplier'),('type_tax_use', '=', 'customer')])
    wtaxf = fields.Selection([('wholding', 'Retencion')], string='Used For')

    @api.multi
    @api.constrains('wtaxf', 'wtax_ids')
    def check_wtaxf(self):
        if self.wtaxf == 'wholding' and self.wtax_ids:
            raise ValidationError(_(
            'no puede tener el check y a la vez codigos de retenciones'))


    @api.multi
    def write(self, vals):
        code_lst = []
        for code in self.wtax_ids:
            code_lst.append(code.name)
        uid = self.env.context.get('uid')
        logvals = {'user': self.env['res.users'].browse(uid).name, 'wh_codes': code_lst, 'acc_name': self.code}
        log_account = self.env['log.account.account'].create(logvals)
        return super(AccountAccount, self).write(vals)
