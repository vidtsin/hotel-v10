# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta
from collections import OrderedDict
from odoo.exceptions import ValidationError, UserError
import xlwt
from cStringIO import StringIO
import base64

class PercepTaxReportWizard(models.TransientModel):
    _name = "percep.tax.report.wizard"

    date_from = fields.Date(string='Date From',
                            required=True,
                            default=datetime.now().strftime('%Y-%m-01'),
                            translate=True)
    date_to = fields.Date(string='Date To', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
                          translate=True)
    journal_ids = fields.Many2many('account.journal',
                                  string="Sale Journals",
                                  translate=True,
                                  domain="[('type', '=', 'sale'),('use_documents', '=', True)]")
    p_journal_ids = fields.Many2many('account.journal',
                                  string="Purchase Journals",
                                  translate=True,
                                  domain="[('type', '=', 'purchase'),('use_documents', '=', True)]")
    tax_percep_ids = fields.Many2many('account.tax',
                                      string="Perception Tax",
                                      translate=True,
                                      domain="[('type_tax_use', '=', 'sale'),('tax_group_id.type', '=', 'perception')]")
    p_tax_percep_ids = fields.Many2many('account.tax',
                                      string="Perception Tax",
                                      translate=True,
                                      domain="[('type_tax_use', '=', 'purchase'),('tax_group_id.type', '=', 'perception')]")
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 required=True,
                                 default=lambda self: self.env.user.company_id,
                                 translate=True)
    group_by_tax = fields.Boolean(string="Group by Perception Tax",translate=True)
    show_comp_cur = fields.Boolean(string="Show Amount in Company Currency",translate=True)
    show_link = fields.Boolean(string="Include Link  (only excel format)",translate=True)
    print_by = fields.Selection([('html','HTML'),('pdf','PDF'),('xls','Xlsx')],
                                string="Printing Options",
                                translate=True,
                                default='html')
    type = fields.Selection([('sale','Sale'),('purchase','Purchase')])
    tax_no_zero = fields.Boolean(string="Show only if Perception is different than 0.00",translate=True)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        self.date_to = str(fields.Datetime.from_string(self.date_from) + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]


    def doit(self):
        filters = list()
        domain = [('date_invoice', '>=', self.date_from),
                  ('date_invoice', '<=', self.date_to),
                  ('state', 'in', ['open','paid'])]
        filters.append(_('dates: ') + str(datetime.strptime(self.date_from, "%Y-%m-%d").strftime("%d-%m-%Y")) + " " +
                       str(datetime.strptime(self.date_to, "%Y-%m-%d").strftime("%d-%m-%Y")))
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
            filters.append(_('Company: ') + self.company_id.name)

        if self.type == 'sale':
            domain.append(('type', 'in', ('out_invoice', 'out_refund')))
            if self.journal_ids:
                domain.append(('journal_id', 'in', self.journal_ids._ids))
                filters.append(_('Journal: ') + str(map(lambda x: x.name, self.journal_ids)))
            if self.tax_percep_ids:
                filters.append(_('Perceptions: ') + str(map(lambda x: x.name, self.tax_percep_ids)))
        if self.type == 'purchase':
            domain.append(('type', 'in', ('in_invoice', 'in_refund')))
            if self.p_journal_ids:
                domain.append(('journal_id', 'in', self.p_journal_ids._ids))
                filters.append(_('Journal: ') + str(map(lambda x: x.name, self.p_journal_ids)))
            if self.p_tax_percep_ids:
                filters.append(_('Perceptions: ') + str(map(lambda x: x.name, self.p_tax_percep_ids)))


        lines = OrderedDict()
        print_data = dict()
        grouped = dict()
        whcodes = dict()
        list_align = list()
        tot_wh = dict()

        if self.type != 'purchase':
            list_titles = [_('Invoice Date'), _('Invoice Nr'), _('Customer Name'), _('Customer ID Nr'),_('Net Amount'),
                       _('Perception Rate %'), _('Jurisdiction'), _('Perception Amount'),_('Tax Name')]
            list_align = ['center', 'center', 'center', 'center', 'right', 'right', 'center', 'right', 'none']
        else:
            list_titles = [_('Invoice Date'), _('Invoice Nr'), _('Customer Name'), _('Customer ID Nr'),
                           _('Jurisdiction'), _('Perception Amount'),_('Tax Name')]
            list_align = ['center', 'center', 'center', 'center', 'center', 'right', 'none']
        if self.show_comp_cur:
            list_titles.append(_('Amount in Company Currency'))
            list_align.append('right')
        if self.print_by == 'xls' and self.show_link:
            list_titles.append(_('Invoice Link'))
            list_align.append('link')

        invoices = self.env['account.invoice'].search(domain,order='date_invoice')
        if invoices:
            index = 0
            for inv in invoices:

                sign = 1
                if inv.type in ('in_refund','out_refund'):
                    sign = -1

                if inv.currency_rate <= 0:
                    currate = 1
                else:
                    currate = inv.currency_rate

                for tax in inv.tax_line_ids:
                    doit = True
                    if self.type == 'sale':
                        if self.tax_percep_ids:
                            if tax.tax_id.id not in self.tax_percep_ids._ids:
                                doit = False
                        else:
                            if tax.tax_id.type_tax_use == 'sale' and tax.tax_id.tax_group_id.type == 'perception':
                                pass
                            else:
                                doit = False
                    if self.type == 'purchase':
                        if self.p_tax_percep_ids:
                            if tax.tax_id.id not in self.p_tax_percep_ids._ids:
                                doit = False
                        else:
                            if tax.tax_id.type_tax_use == 'purchase' and tax.tax_id.tax_group_id.type == 'perception':
                                pass
                            else:
                                doit = False

                    if self.tax_no_zero and tax.amount == 0.0:
                        doit = False

                    if doit:
                        if not tax.tax_id.name in whcodes.keys():
                            whcodes.update({tax.tax_id.name: 0})

                        key = '{:>010s}'.format(str(index))
                        if tax.base > 0:
                            base = tax.amount*100/tax.base
                        else:
                            base = 0.0

                        if self.type != 'purchase':
                            lines.update({key: [str(datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y")),
                                inv.display_name2, inv.partner_id.name, inv.partner_id.main_id_number, tax.base*sign,
                                base, tax.tax_id.jurisdiction_code.name, tax.amount*sign,tax.tax_id.name]})
                        else:
                            lines.update({key: [str(datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y")),
                                inv.display_name2, inv.partner_id.name, inv.partner_id.main_id_number,
                                tax.tax_id.jurisdiction_code.name, tax.amount*sign,tax.tax_id.name]})

                        if self.show_comp_cur:
                            lines[key].append(tax.amount*currate*sign)
                        if self.print_by == 'xls' and self.show_link:
                            if self.type != 'purchase':
                                menu = self.env['ir.model.data'].get_object_reference('account','action_invoice_tree1')
                            else:
                                menu = self.env['ir.model.data'].get_object_reference('account', 'action_invoice_tree2')
                            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + "/web?#id=" + str(inv.id) + \
                                   "&view_type=form&model=account.invoice&action=" + str(menu[1])
                            base_url = base_url.replace("https://", "http://")
                            lines[key].append(base_url)
                        index += 1


                        if not tax.tax_id.name in tot_wh.keys():
                            tot_wh.update({tax.tax_id.name: tax.amount*currate*sign})
                        else:
                            tot_wh[tax.tax_id.name] += tax.amount*currate*sign

            subindex = 0
            if self.group_by_tax:
                testf = False
                for code in whcodes:
                    testf = False
                    for line in lines:
                        if self.type == 'purchase':
                            tt = lines[line][6]
                        else:
                            tt = lines[line][8]
                        if code == tt:
                            key = '{:>010s}'.format(str(subindex))
                            if not testf:
                                if self.type != 'purchase':
                                    if self.print_by != 'excel':
                                        grouped.update({key:[tt,"","","",0,0,"",0,"",0,""]})
                                    else:
                                        grouped.update({key: [tt,"","","",0,0,"",0,"","",0,""]})
                                else:
                                    if self.print_by != 'excel':
                                        grouped.update({key:[tt,"","","",0,0,"",0,""]})
                                    else:
                                        grouped.update({key: [tt,"","","",0,0,"","",0,""]})
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
                return self.env['report'].with_context(landscape=True).get_action(self,'vitt_percep_tax_report.repoort_pdf',data=datas)
            if self.print_by == 'html':
                return self.env['report'].with_context(landscape=True).get_action(self,'vitt_percep_tax_report.repoort_html',data=datas)

        if self.print_by == 'xls':
            print_data = lines
            context = self._context
            filename = _('Perception_Tax_Report.xls')
            workbook = xlwt.Workbook(encoding="UTF-8")
            worksheet = workbook.add_sheet(_('Detail'))

            worksheet.write(0, 0, _('Nombre del Informe: Reporte de percepciones'))
            worksheet.write(1, 0, _('Empresa: ') + self.env.user.company_id.name)

            #print print_data
            line = 3
            row = 0
            for pos, title in enumerate(list_titles):
                if list_align[pos] != 'none':
                    worksheet.write(line, row, title)
                    row += 1
            for data in sorted(print_data.iterkeys()):
                row = 0
                line += 1
                for index, pos in enumerate(list_titles):
                    if list_align[index] != 'none':
                        if list_align[index] != 'link':
                            if list_align[index] == 'center':
                                worksheet.write(line, row, print_data[data][index])
                            else:
                                numberf = float(int(print_data[data][index]*100))/100
                                if numberf != 0:
                                    worksheet.write(line, row, numberf)
                        else:
                            if print_data[data][index]:
                                worksheet.write(line, row, xlwt.Formula('HYPERLINK("%s";"%s")' % (print_data[data][index], 'HTTP-LINK')))
                        row += 1

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
    _name = 'report.vitt_percep_tax_report.repoort_pdf'

    def render_html(self,docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_percep_tax_report.repoort_pdf')

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
        return self.env['report'].render('vitt_percep_tax_report.qweb_customer_invoice_journal', docargs)

class ReportCustomerInvoiceJournalHtml(models.Model):
    _inherit = 'report.vitt_percep_tax_report.repoort_pdf'
    _name = 'report.vitt_percep_tax_report.repoort_html'

