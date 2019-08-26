# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import datetime

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_invoice_open(self):
        for rec in self:
            if rec.journal_id.use_documents:
                if not (rec.partner_id.main_id_number and rec.partner_id.main_id_category_id and
                        rec.partner_id.afip_responsability_type_id):
                    raise UserError(_('Please, Complete Partner fields main id number, category and responsability type first'))
                domain = [
                    ('type', 'in', ['in_invoice', 'in_refund']),
                    ('state', 'not in', ['draft','cancel']),
                    ('partner_id', '=', rec.partner_id.id),
                    ('document_number', '=', rec.document_number),
                    ('journal_document_type_id','=',rec.journal_document_type_id.id),
                    ('company_id','=',rec.company_id.id)
                ]
                invs = rec.env['account.invoice'].search(domain)
                if invs:
                    raise UserError(_('Already Exist an Invoice with the same number, not allowed'))
            if rec.nc_ref_id > 0:
                conf = self.env['ir.config_parameter']
                if conf.get_param('check.no_nc_partial') == 'True':
                    taxes = self.env['ir.values'].get_default('res.company', 'sl_arciba_taxes',company_id=self.env.user.company_id.id)
                    orig_nc = self.env['account.invoice'].search([('id', '=', rec.nc_ref_id)])
                    set_taxes = rec.tax_line_ids.filtered(lambda x: x.tax_id.id in list(taxes))
                    if set_taxes:
                        if not rec.date_invoice:
                            rec.date_invoice = fields.Datetime.now()
                        if datetime.strptime(str(rec.date_invoice), '%Y-%m-%d').month > datetime.strptime(str(orig_nc.date_invoice), '%Y-%m-%d').month \
                                and datetime.strptime(str(rec.date_invoice), '%Y-%m-%d').year == datetime.strptime(str(orig_nc.date_invoice), '%Y-%m-%d').year:
                            raise ValidationError(_('La NC no puede registrar Impuestos de Percepción en un '
                                                    'mes distinto al de la factura de Origen. Por favor, '
                                                    'borre el impuesto de percepción para recalcular los valores.'))
                        if rec.amount_total != orig_nc.amount_total:
                            raise ValidationError(_('Una NC parcial no puede registrar Impuestos de Percepción. '
                                                    'Por favor, borre el impuesto de percepción para recalcular los valores'))

            if self.env['ir.config_parameter'].get_param('check.nc_acc_control') == 'True' and rec.refund_invoice_id:
                found_wh = False
                acc_lst = {}
                acc_lstnc = {}

                inv_orig = rec.refund_invoice_id
                if inv_orig:
                    for inv_line in inv_orig.invoice_line_ids:
                        if inv_line.account_id.wtax_ids:
                            found_wh = True
                        if inv_line.account_id.id in acc_lst.keys():
                            acc_lst[inv_line.account_id.name] = acc_lst[inv_line.account_id.name] + inv_line.price_unit
                        else:
                            acc_lst[inv_line.account_id.name] = inv_line.price_unit

                    if found_wh:
                        for line in rec.invoice_line_ids:
                            if line.account_id.id in acc_lstnc.keys():
                                acc_lstnc[line.account_id.name] = acc_lstnc[line.account_id.name] + line.price_unit
                            else:
                                acc_lstnc[line.account_id.name] = line.price_unit

                        for item in acc_lstnc.keys():
                            if not item in acc_lst.keys():
                                raise ValidationError(_('La factura NC tiene una cuenta que no esta presente en la factura original'))
                            #else:
                                #if acc_lstnc[item] > acc_lst[item]:
                                    #raise Warning(_('La factura de NC tiene un monto mayor que la factura original: ' + str(acc_lstnc[item]) + '>' + str(acc_lst[item])))


            super(AccountInvoice, self).action_invoice_open()

    @api.multi
    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()

        if self.env['ir.config_parameter'].get_param('check.nc_paym') == 'True':
            credit_aml = self.env['account.move.line'].browse(credit_aml_id)
            found_wh = False
            for inv_line in credit_aml.invoice_id.invoice_line_ids:
                if inv_line.account_id.wtax_ids:
                    found_wh = True
            if found_wh:
                if credit_aml.invoice_id.amount_total - credit_aml.invoice_id.residual != 0:
                    raise ValidationError(_('la factura no debe tener ningun pago asociado'))

        if self.env['ir.config_parameter'].get_param('check.nc_acc_control') == 'True':
            accs = self.env['account.account']
            credit_aml = self.env['account.move.line'].browse(credit_aml_id)
            ncs = self.env['account.invoice'].search([('refund_invoice_id.id','=',credit_aml.invoice_id.id)])
            sum_l = sum_l_nc = 0
            if ncs:
                for inv_line in credit_aml.invoice_id.invoice_line_ids:
                    if inv_line.account_id.wtax_ids:
                        accs += inv_line.account_id
                lines = credit_aml.invoice_id.invoice_line_ids.filtered(lambda x: x.account_id in accs)
                sum_l = sum(lines.mapped('price_subtotal'))

                for nc in ncs:
                    if accs:
                        lines_nc = nc.invoice_line_ids.filtered(lambda x: x.account_id in accs)
                        sum_l_nc += sum(lines_nc.mapped('price_subtotal'))
                if sum_l < sum_l_nc:
                    raise ValidationError(_('Diferencias en valores contabilizados. La(s) Cta.(s) %s '
                                            'distinto en la(s) NC(s) que el registrado en la Factura de Proveedor. Por favor, '
                                            'revise los valores ingresados' % (accs.mapped('code'))))

        return super(AccountInvoice, self).assign_outstanding_credit(credit_aml_id)


class AccountInvoiceRefund(models.TransientModel):
    _inherit = 'account.invoice.refund'

    filter_refund = fields.Selection([('refund', 'Create a draft refund'), ('modify', 'Modify: create refund, reconcile and create a new draft invoice')],
        default='refund', string='Refund Method', required=True, help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled')
