# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError


class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    @api.multi
    def compute_withholdings(self):
        for rec in self:
            if rec.partner_type != 'supplier':
                continue
            if rec.payment_ids:
                raise ValidationError(_('No debe Tener Ningun Pago asociado para calcular retenciones'))
            if not rec.company_id.arg_sortdate:
                raise ValidationError(_('Coloque en Compania: ordenar pagos por fecha de vencimiento primero'))
            for invoice in rec.to_pay_move_line_ids:
                if invoice.invoice_id.type == 'in_refund':
                    raise ValidationError(_('Notas de credito sin asociar no son permitidas'))

            self.env['account.tax'].search([
                ('type_tax_use', '=', rec.partner_type),
                ('company_id', '=', rec.company_id.id),
            ]).create_payment_withholdings(rec)

    @api.multi
    def confirm(self):
        res = super(AccountPaymentGroup, self).confirm()
        for rec in self:
            if rec.company_id.automatic_withholdings:
                rec.compute_withholdings()
        return res

class account_payment_group_wizard(models.Model):
    _name = 'account.payment.group.wizard'

    whcod_ids = fields.One2many('account.payment','wiz_rel',string='Codigos Retencion')

    @api.model
    def default_get(self, fields):
        rec = super(account_payment_group_wizard, self).default_get(fields)
        pg_id = self.env['account.payment.group']._context.get('active_id')
        #pg = self.env['account.payment.group'].search([('id', '=', pg_id)])
        #rec['partner_id'] = pg.partner_id.id
        payments = self.env['account.payment'].search([('payment_group_id', '=', pg_id), ('tax_withholding_id', '!=', False)])
        rec['whcod_ids'] = [(6, False, list(payments._ids))]
        return rec

    @api.multi
    def Print_whcert(self):
        datas = {}
        return self.env['report'].with_context(landscape=True).get_action(self, 'account_withholding_automatic.wh_cert', data=datas)


class AccountPaymentGroupWhcert(models.TransientModel):
    _inherit = "account.payment.group.wizard"
    _name = 'report.account.payment.group.wizard'

    @api.model
    def render_html(self, docids, data=None):
        wh_cert = self.env['account.payment.group.wizard'].browse(docids)
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('account_withholding_automatic.wh_cert')
        docargs = {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': wh_cert,
        }
        return self.env['report'].render('account_withholding_automatic.wh_cert', docargs)
