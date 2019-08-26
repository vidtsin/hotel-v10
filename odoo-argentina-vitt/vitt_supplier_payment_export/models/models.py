from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from cStringIO import StringIO
import base64
import unicodedata
import string

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    printable = set(string.printable)
    res =  u"".join([c for c in nfkd_form if not unicodedata.combining(c)])[:30]
    return filter(lambda x: x in printable, res)

class AccountJurnal(models.Model):
    _inherit = "account.journal"

    company_bank_id = fields.Char(string="Company Bank ID",transalte=True)
    account_bank_export = fields.Char(
        string="Account for Bank Export",
        help="MMFFFFFFFDCCCE, donde: MM: Moneda {00=Pesos, 02=Dolares}, FFFFFFF: Folio de la cuenta, D: Digito de control 1, CCC: Sucursal, E: Digito de control 2. ",
        translate=True,
    )

class AccountExports(models.Model):
    _name = "account.exports"

    name = fields.Char(string="Description",translate=True,required=True)
    payment_form_id = fields.Many2one('account.journal',
                                      string="Payment Form",
                                      translate=True,
                                      required=True,
                                      domain="[('type', 'in', ('bank','cash'))]")
    bank_sequence = fields.Integer(string="Sequencia Bancaria")

class Resusers(models.Model):
    _inherit = "res.users"

    allow_mod_export = fields.Boolean(string="Allow mod. for exported payments",translate=True)

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    txt_export_date = fields.Datetime(string="Fecha y Hora",translate=True)
    export_reference = fields.Char(string="Referencia",traslate=True)

    @api.multi
    def confirm(self):
        prev_apg = self.env['account.payment.group'].search([('state', '=', 'confirmed')])
        for apg in prev_apg:
            for prev_aml in apg.to_pay_move_line_ids:
                for rec in self:
                    for aml in rec.to_pay_move_line_ids:
                        if aml.invoice_id == prev_aml.invoice_id:
                            raise UserError(_('There is at least 1 invoice affected to another Payment, no allowed'))
        return super(AccountPaymentGroup, self).confirm()

    @api.multi
    def cancel(self):
        for rec in self:
            if rec.txt_export_date:
                raise UserError(_('Already Exported to Bank, no allowed'))
        return super(AccountPaymentGroup, self).cancel()


class AccountExportWizard(models.TransientModel):
    _name = "account.export.wizard"

    export_type_id = fields.Many2one('account.exports',string="Export Type",translate=True,required=True)
    export_reference = fields.Char(string="Export Reference",translate=True,required=True)

    def doit(self):
        context = self._context
        filename= 'GALICIA.txt'

        apgs = self.env['account.payment.group'].browse(self._context.get('active_ids'))
        tstr = ""
        tot = 0
        tot_pes = 0.0
        for apg in apgs:
            if apg.state != 'confirmed':
                raise UserError(_('One or more of the selected payments is not in confirmed State'))

            if apg.txt_export_date:
                raise UserError(_('One or more of the selected payments has already been exported'))

            has_paym_type = False
            for payment in apg.payment_ids:
                if payment.journal_id.id == self.export_type_id.payment_form_id.id:
                    tot += 1
                    tot_pes += payment.amount
                    if has_paym_type:
                        raise UserError(_('The Payment Method has been used more than once in Payment Please check ' \
                            'and correct this issue. If you are exporting bank payments, then the Payment Method can ' \
                            'be used only once per supplier payment record'))
                    else:
                        has_paym_type = True
            if not has_paym_type:
                raise UserError(_('The payment form and export type are not compatible'))

        tstr += "PC"
        tstr += "T"
        if self.export_type_id.payment_form_id.company_bank_id:
            tstr += "{:0<2}".format(self.export_type_id.payment_form_id.company_bank_id)
        else:
            tstr += "{:0<2}".format('0')
        tstr += "{:0>6}".format(str(self.export_type_id.bank_sequence))
        self.export_type_id.write({'bank_sequence':self.export_type_id.bank_sequence+1})
        tstr += datetime.now().strftime('%d%m%Y')
        if self.export_type_id.payment_form_id.account_bank_export:
            tstr += self.export_type_id.payment_form_id.account_bank_export
        else:
            tstr += "{:0<14}".format('0')
        tstr += "{:<40}".format(remove_accents(apg.company_id.name[0:40]))
        tstr += "{:0>6}".format(str(len(self._context.get('active_ids'))))
        tstr += "{:0>17}".format(str(int(tot_pes*100)))
        tstr += datetime.now().strftime('%d%m%Y')
        tstr += datetime.now().strftime('%d%m%Y')
        tstr += '000'
        tstr += "{:0>54}".format('0')
        tstr += '01'
        tstr += "{:0>22}".format('0')
        tstr += "{:0>126}".format('0')
        tstr += "{:>5}".format(' ')
        tstr += '\r\n'
        nr_of_regs = 1
        for apg in apgs:
            for payment in apg.payment_ids:
                if payment.journal_id.id == self.export_type_id.payment_form_id.id:
                    tstr += 'PD'
                    tstr += "{:0>6}".format(str(nr_of_regs))
                    nr_of_regs += 1
                    tstr += "{:0>17}".format(str(int(payment.amount*100)))
                    tstr += '001'
                    bank = self.env['res.partner.bank'].search([
                        ('bank_id', '=', payment.journal_id.bank_id.id),
                        ('partner_id', '=', apg.partner_id.id)],limit=1)
                    tstr += "{:>22}".format(bank.cbu)
                    tstr += datetime.now().strftime('%d%m%Y')
                    tstr += "{:<50}".format(remove_accents(apg.partner_id.name[0:50]))
                    tstr += "{:<30}".format(remove_accents(apg.partner_id.street[0:30]))
                    tstr += "{:<20}".format(remove_accents(apg.partner_id.city[0:20]))
                    tstr += "{:<6}".format(apg.partner_id.zip[0:6])
                    if apg.partner_id.phone:
                        tstr += "{:<15}".format(apg.partner_id.phone[0:15])
                    else:
                        tstr += "{:<15}".format(' ')
                    tstr += "{:<15}".format(apg.partner_id.main_id_number[0:15])
                    tstr += "{:0>35}".format('0')
                    tstr += "{:0>2}".format('0')
                    tstr += "{:0>2}".format('0')
                    tstr += "{:>86}".format(' ')
                    tstr += '\r\n'


        fp = StringIO()
        fp.write(tstr)
        export_id = self.env['sire.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename }).id
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sire.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }


