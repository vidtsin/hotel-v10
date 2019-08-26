from odoo import models, fields, api, _
from datetime import datetime
from dateutil import relativedelta
from collections import OrderedDict
import xlwt
from cStringIO import StringIO
import base64

class AccountPaymentWhwizard(models.TransientModel):
    _name = 'account.payment.whwizard'

    date_from = fields.Date(string='Date From', required=True, default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True, default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    partner_id = fields.Many2many('res.partner', string="Suppliers", translate=True, domain="[('supplier', '=', True)]")
    partner2_id = fields.Many2many('res.partner', string="Customers", translate=True, domain="[('customer', '=', True)]")
    wh_tax_code = fields.Many2many(
        'account.tax',
        domain="[('type_tax_use','=','supplier'),('active','=',True),('withholding_type','in',['tabla_ganancias','arba_ws','based_on_rule'])]",
        string="Withholding Tax Code",
        translate=True,
    )
    wh_tax_code2 = fields.Many2many(
        'account.tax',
        domain="[('type_tax_use','=','customer'),('active','=',True)]",
        string="Withholding Tax Code",
        translate=True,
    )
    journal_id = fields.Many2many('account.journal',
        string="Withholding Tax Journal",
        domain="[('type', 'in', ['bank', 'cash']), "
               "('outbound_payment_method_ids.code', 'in', ['withholding']),"
               "('outbound_payment_method_ids.payment_type', '=', 'outbound')]",
        translate=True,
    )
    journal2_id = fields.Many2many('account.journal',
        string="Withholding Tax Journal",
        domain="[('type', 'in', ['bank', 'cash']),('inbound_payment_method_ids.code', 'in', ['withholding']),('inbound_payment_method_ids.payment_type', '=', 'inbound')]",
        translate=True,
    )
    company_id = fields.Many2one('res.company', string="Company", translate=True, default=lambda self: self.env.user.company_id)
    wh_group_by = fields.Boolean(string="Group by Withholding Tax",translate=True)
    include_link = fields.Boolean(string="Include No. Link", translate=True)
    print_by = fields.Selection([('html','HTML'),('pdf','PDF'),('excel','Export xlsx')],string="Printing Options",default="html",required=True)
    type = fields.Char(size=64)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        self.date_to = str(fields.Datetime.from_string(self.date_from) + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]


    def doit(self):
        filters = list()
        domain = [('payment_date', '>=', self.date_from), ('payment_date', '<=', self.date_to), ('state', 'in', ['posted'])]
        if self.type == 'customer':
            domain.append(('payment_type', '=', 'inbound'))
        if self.type == 'supplier':
            domain.append(('payment_type', '=', 'outbound'))
        filters.append(_('dates: ') + str(datetime.strptime(self.date_from, "%Y-%m-%d").strftime("%d-%m-%Y")) + " " +
                       str(datetime.strptime(self.date_to, "%Y-%m-%d").strftime("%d-%m-%Y")))
        if self.partner_id and self.type == "supplier":
            domain.append(('partner_id', 'in', self.partner_id._ids))
            filters.append(_('Suppliers: ') + str(map(lambda x: x.name, self.partner_id)))
        if self.partner2_id and self.type == "customer":
            domain.append(('partner_id', 'in', self.partner2_id._ids))
            filters.append(_('Customers: ') + str(map(lambda x: x.name, self.partner2_id)))
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
            filters.append(_('Company: ') + self.company_id.name)

        if self.type == 'customer':
            if self.wh_tax_code2:
                domain.append(('tax_withholding_id', 'in', self.wh_tax_code2._ids))
                filters.append(_('Withholding Tax: ') + str(map(lambda x: x.name, self.wh_tax_code2)))
            else:
                domain.append(('tax_withholding_id', '!=', False))

        if self.type == 'supplier':
            if self.wh_tax_code:
                domain.append(('tax_withholding_id', 'in', self.wh_tax_code._ids))
                filters.append(_('Withholding Tax: ') + str(map(lambda x: x.name, self.wh_tax_code)))
            else:
                domain.append(('tax_withholding_id', '!=', False))

        if self.journal_id and self.type == 'supplier':
            domain.append(('journal_id', '=', self.journal_id._ids))
            filters.append(_('Journal: ') + str(map(lambda x: x.name, self.journal_id)))
        if self.journal2_id and self.type == 'customer':
            domain.append(('journal_id', '=', self.journal2_id._ids))
            filters.append(_('Journal: ') + str(map(lambda x: x.name, self.journal2_id)))

        lines = OrderedDict()
        print_data = dict()
        grouped = dict()
        whcodes = dict()
        list_align = list()
        tot_wh = dict()

        if self.type == 'supplier':
            list_titles = [_('Supplier Id No'), _('Supplier Name'), _('Payment No'), _('Supplier Invoice No'),
                    _('Withholding Certificate No'), _('Withholding Tax'), _('Withholdable Amount'), _('Withholding Rate'),
                    _('Withholding Value'),_('MB1 Amount')]
            list_align = ['center', 'center', 'center', 'center', 'center', 'center', 'right', 'right', 'right', 'right']
            if self.print_by == 'excel':
                list_titles.append(_('Payment Date'))
                list_align.append('center')
            if self.print_by == 'excel' and self.include_link:
                list_titles.append(_('Payment No. Link'))
                list_align.append('link')
        if self.type == 'customer':
            list_titles = [_('Customer Id No'), _('Customer Name'), _('Receipt No'), _('Customer Invoice No'),
                    _('Withholding Certificate No'), _('Withholding Tax'), _('Withholdable Amount'), _('Withholding Rate'),
                    _('Withholding Value'),_('MB1 Amount')]
            list_align = ['center', 'center', 'center', 'center', 'center', 'center', 'right', 'right', 'right', 'right']
            if self.print_by == 'excel':
                list_titles.append(_('Receipt Date'))
                list_align.append('center')
            if self.print_by == 'excel' and self.include_link:
                list_titles.append(_('Receipt No. Link'))
                list_align.append('link')


        payments = self.env['account.payment'].search(domain,order="payment_date")
        print domain
        if payments:
            #types = dict(payments[0].tax_withholding_id.tax_group_id._fields['name']._description_selection(self.env))
            index = 0
            for pay in payments:
                if True:
                #if self.wh_group_by:
                    if not pay.tax_withholding_id.name in whcodes.keys():
                        whcodes.update({pay.tax_withholding_id.name: 0})

                if not pay.partner_id.main_id_number in lines.keys():
                    key = '{:>010s}'.format(str(index))
                    if self.type == 'supplier':
                        lines.update({key: [pay.partner_id.main_id_number, pay.partner_id.name,
                            pay.payment_group_id.display_name, pay.vendorbill.display_name2, pay.withholding_number,
                            pay.tax_withholding_id.name, pay.withholdable_invoiced_amount, pay.wh_perc, pay.amount,
                            pay.amount*pay.manual_currency_rate]})
                    if self.type == 'customer':
                        lines.update({key: [pay.partner_id.main_id_number, pay.partner_id.name,
                            pay.payment_group_id.display_name, pay.customerbill.display_name2, pay.withholding_number,
                            pay.tax_withholding_id.name, pay.withholding_base_amount, pay.wh_perc, pay.amount,
                            pay.amount*pay.manual_currency_rate]})
                    if self.print_by == 'excel':
                        lines[key].append(datetime.strptime(pay.payment_date, "%Y-%m-%d").strftime("%d-%m-%Y"))

                    if self.print_by == 'excel' and self.include_link:
                        if self.type == 'customer':
                            menu = self.env['ir.model.data'].get_object_reference('account_payment_group','action_account_payments_group')
                        if self.type == 'supplier':
                            menu = self.env['ir.model.data'].get_object_reference('account_payment_group','action_account_payments_group_payable')
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web?#id=" + str(
                            pay.payment_group_id.id) + \
                                   "&view_type=form&model=account.payment.group&action=" + str(menu[1])
                        base_url = base_url.replace("https://", "http://")
                        lines[key].append(base_url)
                    index += 1

                if not pay.tax_withholding_id.name in tot_wh.keys():
                    tot_wh.update({pay.tax_withholding_id.name: pay.amount})
                else:
                    tot_wh[pay.tax_withholding_id.name] += pay.amount

            subindex = 0
            if self.wh_group_by:
                testf = False
                for code in whcodes:
                    testf = False
                    for line in lines:
                        if code == lines[line][5]:
                            key = '{:>010s}'.format(str(subindex))
                            if not testf:
                                if self.print_by != 'excel':
                                    grouped.update({key:[lines[line][5],"","","","","",0,0,0,0]})
                                else:
                                    grouped.update({key: [lines[line][5], "", "", "", "", "", 0, 0, 0, 0, "", ""]})
                                testf = True
                                subindex += 1
                            key = '{:>010s}'.format(str(subindex))
                            grouped.update({key:lines[line]})
                            subindex += 1
                #print grouped
                lines = grouped

        if len(lines) > 5000 and self.print_by in ['html','pdf']:
            raise UserError(_("report has more than 5000 lines, please use Excel instead"))


        if self.print_by in ('pdf', 'html'):
            datas = {
                'print_data': lines,
                'list_titles': list_titles,
                'filters2': filters,
                'list_align': list_align,
                'type': self.type,
                'whcodes': whcodes,
                'tot_wh': tot_wh,
            }
            if self.print_by == 'pdf':
                return self.env['report'].with_context(landscape=True).get_action(self,'vitt_withholding_tax_report.repoort_pdf',data=datas)
            if self.print_by == 'html':
                return self.env['report'].with_context(landscape=True).get_action(self,'vitt_withholding_tax_report.repoort_html',data=datas)

        if self.print_by == 'excel':
            print_data = lines
            context = self._context
            filename = _('partners_invoices_journals.xls')
            workbook = xlwt.Workbook(encoding="UTF-8")
            worksheet = workbook.add_sheet(_('Detail'))

            worksheet.write(0, 0, _('Nombre del Informe: Reporte de retenciones'))
            worksheet.write(1, 0, _('Empresa: ') + self.env.user.company_id.name)

            line = 3
            row = 0
            for title in list_titles:
                worksheet.write(line, row, title)
                row += 1
            for data in sorted(print_data.iterkeys()):
                row = 0
                line += 1
                for index, pos in enumerate(list_titles):
                    if list_align[index] != 'link':
                        if list_align[index] == 'center':
                            worksheet.write(line, row, print_data[data][index])
                        else:
                            numberf = float(int(print_data[data][index]*100))/100
                            if numberf > 0:
                                worksheet.write(line, row, numberf)
                    else:
                        if print_data[data][index]:
                            worksheet.write(line, row, xlwt.Formula('HYPERLINK("%s";"%s")' % (print_data[data][index], 'HTTP-LINK')))
                    row += 1

            if True:
            #if self.wh_group_by:
                row = 0
                line += 3
                worksheet.write(line, row, _("Totales Agrupados"))
                for cur in tot_wh:
                    line += 1
                    row = 0
                    worksheet.write(line, row, cur)
                    row += 1
                    number = float(int(tot_wh[cur]*100))/100
                    worksheet.write(line, row, number)


            fp = StringIO()
            workbook.save(fp)
            export_id = self.env['excel.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename }).id
            fp.close()
            return{
                'view_mode': 'form',
                'res_id': export_id,
                'res_model': 'excel.extended',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }



class ReportCustomerInvoiceJournalPdf(models.Model):
    _name = 'report.vitt_withholding_tax_report.repoort_pdf'

    def render_html(self,docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_withholding_tax_report.repoort_pdf')

        #print sorted(data['print_data'].items(), key=lambda x: x[0])
        docargs = {
            'doc_ids': {},
            'doc_model': report.model,
            'print_data': sorted(data['print_data'].items(), key=lambda x: x[0]),
            'list_titles': data['list_titles'],
            'filters2': data['filters2'],
            'list_align': data['list_align'],
            'type': data['type'],
            'whcodes': data['whcodes'],
            'tot_wh': data['tot_wh'],
        }
        return self.env['report'].render('vitt_withholding_tax_report.qweb_customer_invoice_journal', docargs)

class ReportCustomerInvoiceJournalHtml(models.Model):
    _inherit = 'report.vitt_withholding_tax_report.repoort_pdf'
    _name = 'report.vitt_withholding_tax_report.repoort_html'

