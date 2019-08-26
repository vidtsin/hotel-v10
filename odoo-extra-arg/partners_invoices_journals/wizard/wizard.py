from odoo import models, fields, api, _, tools
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import UserError
from collections import OrderedDict
import xlwt
from cStringIO import StringIO
import base64

class WizardCustomerInvoiceJournal(models.TransientModel):
    _name = 'wizard.customer.invoice.journal'

    date_from = fields.Date(string='Date From', required=True,default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
                          default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    partner_ids = fields.Many2many('res.partner',string="Customer",domain=[('customer', '=', True)])
    partner2_ids = fields.Many2many('res.partner', string="Supplier", domain=[('supplier', '=', True)])
    categ_ids = fields.Many2many('res.partner.category',string="Category")
    user_id = fields.Many2one('res.users',string="Sales Person")
    salesteam_id = fields.Many2one('crm.team',string="Sales Team")
    journal_ids = fields.Many2many('account.journal',string="Journal",domain="[('type', '=', 'sale')]")
    journal2_ids = fields.Many2many('account.journal',string="Journal",domain="[('type', '=', 'purchase')]")
    paym_term_id = fields.Many2one('account.payment.term',string="Payment Term")
    hanal_tag_ids = fields.Many2many('account.analytic.tag',string="Analytic Tags (header)")
    ranal_tag_ids = fields.Many2many('account.analytic.tag',string="Analytic Tags (rows)")
    anal_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
    company_id = fields.Many2one('res.company',string="Company",default=lambda self: self.env.user.company_id.id)
    draft = fields.Boolean(string="Draft",default=True)
    open = fields.Boolean(string="Open",default=True)
    paid = fields.Boolean(string="Paid")
    #states = fields.Selection([('draft','Draft'),('open','Open'),('paid','Paid')],string="States")
    sort_by = fields.Selection([('date_invoice','By Invoice Date'),
                                ('date','By Invoice Acc. Date'),
                                ('display_name2','By Invoice Number')],
                               string="Sort by",default="date_invoice",required=True)
    invoice_type = fields.Boolean(string="Invoices",default=True)
    refund_type = fields.Boolean(string="Refund Invoices",default=True)
    show_comp_currency = fields.Boolean(string="Show Totals In Company Currency")
    show_inv_taxes = fields.Boolean(string="Show Invoice Taxes")
    show_exch_rates = fields.Boolean(string="Show Invoice Exchange Rate")
    artmode = fields.Selection([('overview','Overview'),('detailed','Detailed')],default="overview",string="Level of Detail",required=True)
    print_by = fields.Selection([('html','HTML'),('pdf','PDF'),('excel','Export xlsx')],string="Printing Options",default="html",required=True)
    type = fields.Char(size=64)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        self.date_to = str(fields.Datetime.from_string(self.date_from) + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10]


    def setinset(self, list1, list2):
        foundf = False
        for tag in list1:
            if tag in list2:
                foundf = True
                break
        return foundf

    def execute(self):
        if not self.draft and not self.open and not self.paid:
            raise UserError(_("you should select at least 1 State"))
        if not self.invoice_type and not self.refund_type:
            raise UserError(_("you should select at least 1 Invoice Type"))
        if self.print_by == 'html' and self.artmode == 'detailed':
            raise UserError(_("To run this report in the Detailed version you cannot choose 'HTML' "
                              "as the printing Option. Please choose PDF or xlsx and try again"))

        filters = list()
        l = ""
        inv_obj = self.env['account.invoice']
        domain = [('date_invoice', '>=', self.date_from),('date_invoice', '<=', self.date_to)]
        if self.type == 'customer' and self.partner_ids.ids:
            domain.append(('partner_id', 'in', list(self.partner_ids.ids)))
            l = _("Partners: ")
            for p in self.partner_ids:
                l += p.name + ","
            filters.append(l)
        if self.type == 'supplier' and self.partner2_ids.ids:
            domain.append(('partner_id', 'in', list(self.partner2_ids.ids)))
            l = _("Partners: ")
            for p in self.partner2_ids:
                l += p.name + ","
            filters.append(l)
        if self.categ_ids:
            domain.append(('partner_id.category_id', 'in', self.categ_ids._ids))
            l = _("Categories: ")
            for p in self.categ_ids:
                l += p.name + ","
            filters.append(l)
        if self.user_id:
            domain.append(('user_id', '=', self.user_id.id))
            filters.append(_("User: ") + self.user_id.name)
        if self.salesteam_id:
            domain.append(('team_id', '=', self.salesteam_id.id))
            filters.append(_("SalesTeam: ") + self.salesteam_id.name)
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids._ids))
            l = _("Journals: ")
            for p in self.journal_ids:
                l += p.name + ","
            filters.append(l)
        if self.paym_term_id:
            domain.append(('payment_term_id', '=', self.paym_term_id.id))
            filters.append(_("Payment Term: ") + self.paym_term_id.name)
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
            filters.append(_("Company: ") + self.company_id.name)

        state = list()
        if self.open:
            state.append('open')
        if self.draft:
            state.append('draft')
        if self.paid:
            state.append('paid')
        domain.append(('state', 'in', state))
        filters.append(_("States: ") + tools.ustr(state))

        l = "["
        type = list()
        if self.type == 'customer':
            if self.invoice_type:
                type.append('out_invoice')
                l += _("Sales Invoices") + ','
            if self.refund_type:
                type.append('out_refund')
                l += _("Sales Credit Notes") +','
        if self.type == 'supplier':
            if self.invoice_type:
                type.append('in_invoice')
                l += _("Purchase Invoices") + ','
            if self.refund_type:
                type.append('in_refund')
                l += _("Purchase Credit Notes") + ','
        l += "]"
        domain.append(('type', 'in', type))
        filters.append(_("Types: ") + l)
        filters.append(_("Period: ") + self.date_from + ':' + self.date_to)

        print_data = dict()
        inv_qty = dict()
        footer_cur = dict()
        footer_comp_cur = dict()
        curtotals = dict()
        list_titles = list()
        list_align = list()
        list_data = list()
        oldindex = -1
        tot_cur = 0.0

        invoices = inv_obj.search(domain,order=self.sort_by)
        for index, inv in enumerate(invoices):
            if inv.type in ('out_invoice','in_invoice'):
                sign = 1
            if inv.type in ('out_refund','in_refund'):
                sign = -1
            if self.artmode == 'overview':
                showf = True
                if self.hanal_tag_ids:
                    if not self.setinset(self.hanal_tag_ids._ids, inv.analytic_tag_ids._ids):
                        showf = False
                if showf:
                    list_data = list()
                    list_titles = list()
                    list_align = list()
                    if inv.display_name2:
                        list_data.append(inv.display_name2)
                    else:
                        list_data.append("BORRADOR")
                    list_titles.append(_("Invoice Nr"))
                    list_align.append('center')

                    list_data.append(datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y"))
                    list_titles.append(_("Invoice Date"))
                    list_align.append('center')

                    list_data.append(inv.partner_id.name[:30])
                    list_titles.append(_("Customer"))
                    list_align.append('center')

                    if inv.type in ('out_invoice', 'in_invoice'):
                        list_data.append(_("FC"))
                        list_titles.append(_("Invoice Type"))
                        list_align.append('center')
                    if inv.type in ('out_refund', 'in_refund'):
                        list_data.append("NC")
                        list_titles.append(_("Invoice Type"))
                        list_align.append('center')

                    list_data.append(inv.amount_untaxed*sign)
                    list_titles.append(_("Untaxed Amount"))
                    list_align.append('right')

                    if self.show_inv_taxes:
                        list_data.append(inv.amount_tax*sign)
                        list_titles.append(_("Taxes"))
                        list_align.append('right')

                    list_data.append(inv.amount_total*sign)
                    list_titles.append(_("Total Amount (incl Tax)"))
                    list_align.append('right')

                    if self.show_exch_rates:
                        list_data.append(inv.currency_rate)
                        list_titles.append(_("Exchange Rate"))
                        list_align.append('center')

                    list_data.append(inv.currency_id.name)
                    list_titles.append(_("Currency"))
                    list_align.append('center')

                    if self.show_comp_currency:
                        list_data.append(inv.amount_total * inv.currency_rate * sign)
                        list_titles.append(_("Total In Company Currency"))
                        list_align.append('right')
                        tot_cur += inv.amount_total * inv.currency_rate * sign

                    key = '{:>010s}:{:>010s}'.format(str(index), '0')
                    print_data.update({key: list_data})

                    if not inv.currency_id.name in footer_cur.keys():
                        footer_cur.update({inv.currency_id.name:inv.amount_total})
                    else:
                        footer_cur[inv.currency_id.name] += inv.amount_total

                    if self.show_comp_currency:
                        if not inv.company_id.currency_id.name in footer_comp_cur.keys():
                            footer_comp_cur.update({inv.company_id.currency_id.name:(inv.amount_total*inv.currency_rate*sign)})
                        else:
                            footer_comp_cur[inv.company_id.currency_id.name] += (inv.amount_total*inv.currency_rate*sign)

                    if not inv.currency_id.name in curtotals.keys():
                        curtotals.update({inv.currency_id.name: inv.amount_total*sign})
                    else:
                        curtotals[inv.currency_id.name] += inv.amount_total*sign

                    if not _("Invoice Qty") in inv_qty.keys():
                        inv_qty.update({_("Invoice Qty"): 1})
                    else:
                        inv_qty[_("Invoice Qty")] += 1

            if self.artmode == 'detailed':
                for indexl, line in enumerate(inv.invoice_line_ids):
                    showf = True
                    if self.ranal_tag_ids:
                        if not self.setinset(self.ranal_tag_ids._ids, line.analytic_tag_ids._ids):
                            showf = False
                    if self.anal_account_id:
                        if self.anal_account_id.id != line.account_analytic_id.id:
                            showf = False
                    if showf:
                        if oldindex != index:
                            oldindex = index
                            if not _("Invoice Qty") in inv_qty.keys():
                                inv_qty.update({_("Invoice Qty"): 1})
                            else:
                                inv_qty[_("Invoice Qty")] += 1

                        list_data = list()
                        list_titles = list()
                        val = 0.0
                        price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.invoice_line_tax_ids.compute_all(price_unit, inv.currency_id, line.quantity,
                                                                      line.product_id, inv.partner_id)['taxes']
                        for tax in taxes:
                            vals = inv._prepare_tax_line_vals(line, tax)
                            val += vals['amount']

                        if inv.display_name2:
                            list_data.append(inv.display_name2)
                        else:
                            list_data.append("BORRADOR")
                        list_titles.append(_("Invoice Nr"))
                        list_align.append('center')

                        list_data.append(datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y"))
                        list_titles.append(_("Invoice Date"))
                        list_align.append('center')

                        list_data.append(inv.partner_id.name[:30])
                        list_titles.append(_("Customer"))
                        list_align.append('center')

                        if inv.type in ('out_invoice', 'in_invoice'):
                            list_data.append(_("FC"))
                            list_titles.append(_("Invoice Type"))
                            list_align.append('center')
                        if inv.type in ('out_refund', 'in_refund'):
                            list_data.append("NC")
                            list_titles.append(_("Invoice Type"))
                            list_align.append('center')

                        list_data.append(line.product_id.name)
                        list_titles.append(_("Product"))
                        list_align.append('center')

                        list_data.append(line.quantity)
                        list_titles.append(_("Qty"))
                        list_align.append('right')

                        list_data.append(price_unit*sign)
                        list_titles.append(_("Unit Price"))
                        list_align.append('right')

                        list_data.append(line.price_subtotal*sign)
                        list_titles.append(_("Untaxed Amount"))
                        list_align.append('right')

                        if self.show_inv_taxes:
                            list_data.append(val*sign)
                            list_titles.append(_("Taxes"))
                            list_align.append('right')

                        list_data.append(line.price_subtotal*sign + val*sign)
                        list_titles.append(_("Total Amount (incl Tax)"))
                        list_align.append('right')

                        if self.show_exch_rates:
                            list_data.append(inv.currency_rate)
                            list_titles.append(_("Exchange Rate"))
                            list_align.append('right')

                        list_data.append(inv.currency_id.name)
                        list_titles.append(_("Currency"))
                        list_align.append('center')

                        if self.show_comp_currency:
                            list_data.append((line.price_subtotal+val)*inv.currency_rate*sign)
                            list_titles.append(_("Total In Company Currency"))
                            list_align.append('right')

                        key = '{:>010s}:{:>010s}'.format(str(index), str(indexl))
                        print_data.update({key: list_data})

                        if not inv.currency_id.name in curtotals.keys():
                            curtotals.update({inv.currency_id.name: line.price_subtotal*sign})
                        else:
                            curtotals[inv.currency_id.name] += line.price_subtotal*sign
                if self.show_comp_currency:
                    tot_cur += inv.amount_total * inv.currency_rate * sign

        if len(print_data) > 5000 and self.print_by in ['html','pdf']:
            raise UserError(_("report has more than 5000 lines, please use Excel instead"))

        #print print_data
        #print list_titles
        if self.print_by in ['html','pdf']:
            datas = {
                'print_data': print_data,
                'inv_qty': inv_qty,
                'footer_cur': footer_cur,
                'footer_comp_cur': footer_comp_cur,
                'curtotals': curtotals,
                'list_titles': list_titles,
                'filters2': filters,
                'list_align': list_align,
                'type': self.type,
                'tot_cur': tot_cur,
            }

            if self.print_by == 'pdf':
                return self.env['report'].with_context(landscape=True).get_action(self,'partners_invoices_journals.repoort_pdf',data=datas)
            if self.print_by == 'html':
                return self.env['report'].with_context(landscape=True).get_action(self,'partners_invoices_journals.repoort_html',data=datas)

        if self.print_by == 'excel':
            context = self._context
            filename = _('partners_invoices_journals.xls')
            workbook = xlwt.Workbook(encoding="UTF-8")
            worksheet = workbook.add_sheet(_('Detail'))

            worksheet.write(0, 0, _('Nombre del Informe: Partners Invoices Journals'))
            worksheet.write(1, 0, _('Empresa: ') + self.env.user.company_id.name)

            line = 3
            row = 0
            for title in list_titles:
                worksheet.write(line, row, title)
                row += 1
            for data in sorted(print_data.iterkeys()):
                row = 0
                print data
                line += 1
                for index, pos in enumerate(list_titles):
                    worksheet.write(line, row, print_data[data][index])
                    row += 1
            if tot_cur > 0:
                line += 1
                row -= 1
                worksheet.write(line, row, tot_cur)

            row = 0
            line += 3
            worksheet.write(line, row, "Totales por Moneda")
            for cur in curtotals:
                line += 1
                row = 0
                worksheet.write(line, row, cur)
                row += 1
                worksheet.write(line, row, curtotals[cur])


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
    _name = 'report.partners_invoices_journals.repoort_pdf'

    def render_html(self,docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('partners_invoices_journals.repoort_pdf')

        docargs = {
            'doc_ids': {},
            'doc_model': report.model,
            'print_data': sorted(data['print_data'].items(), key=lambda x: x[0]),
            'inv_qty': data['inv_qty'],
            'footer_cur': data['footer_cur'],
            'footer_comp_cur': data['footer_comp_cur'],
            'curtotals': data['curtotals'],
            'list_titles': data['list_titles'],
            'filters2': data['filters2'],
            'list_align': data['list_align'],
            'type': data['type'],
            'tot_cur': data['tot_cur'],
        }
        return self.env['report'].render('partners_invoices_journals.qweb_customer_invoice_journal', docargs)

class ReportCustomerInvoiceJournalHtml(models.Model):
    _inherit = 'report.partners_invoices_journals.repoort_pdf'
    _name = 'report.partners_invoices_journals.repoort_html'

