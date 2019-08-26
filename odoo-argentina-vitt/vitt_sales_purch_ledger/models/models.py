# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import xlwt
from cStringIO import StringIO
import base64
from odoo import conf
import imp
from decimal import *
import copy

class ReportSlLedger(models.TransientModel):
    _name = "report.pl.ledger"

    partner_id = fields.Many2many('res.partner',string="partner",translate=True,domain="[('supplier','=',True)]")
    category_id = fields.Many2many('res.partner.category', column1='partner_id',column2='category_id',
                                   string='Partner Tags',translate=True)
    user_id = fields.Many2one('res.users',string="Resposible",translate=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag',string="Analytic Tags (Header)",translate=True)
    currency_id = fields.Many2one('res.currency',string="Currency",translate=True)
    date = fields.Date(string='To Date', required=True,default=datetime.now().strftime('%Y-%m-%d'))
    sl_cred_acc_ids = fields.Many2many('account.account',domain=[('user_type_id.type','=','payable')],string="Creditors Account",translate=True)
    Amounts = fields.Selection([('comp_cur', 'In Company Currency'),('inv_cur', 'In Register Currency')],
                               string='Amounts', default='comp_cur', translate=True)
    on_acc = fields.Selection([('include', 'Include on Account'),('only', 'Only on Account'),('skip', 'Skip on Account')],
                               string='On Account', default='include', translate=True)
    state = fields.Selection([('open', 'Open'),('overdue', 'Overdue')],string='State', default='open', translate=True)
    function = fields.Selection([('overview', 'Overview'),('open_balance', 'Open Balance')],
                               string='Function', default='overview', translate=True)
    tot_comp_cur = fields.Boolean(string="Show totals in Company Currency", default=True,translate=True)
    excl_dispute = fields.Boolean(string="Excluir Facturas Cuestionadas",translate=True)
    date_time_print = fields.Boolean(string="Print report print Date & Time", default=True,translate=True)
    today = fields.Datetime(default=lambda self: fields.Datetime.now())
    ex_rate_option = fields.Selection(
        [('ex_rate_reg', 'Use Ex. Rate from Register'),('ex_rate_other', 'Use Another Ex. Rate')],
        default='ex_rate_reg', translate=True,
    )
    ex_rate = fields.Float(digits=(7, 5), string="Rate",translate=True)
    sort = fields.Selection(
        [('due_date', 'By Due Date'), ('reg_date', 'By Register Date')],
        default='due_date', translate=True,
    )


    def plist(self,plist):
        res = ""
        for p in plist:
            res += ',' + p.name
        return res

    @api.multi
    def ledger_pl_report_html(self):

        meet_date = fields.Datetime.from_string(self.today)
        s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id.name

        datas = {
            'partner_id': self.partner_id.ids,
            'category_id': self.category_id.ids,
            'user_id': self.user_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'sl_cred_acc_ids': self.sl_cred_acc_ids.ids,
            'Amounts': self.Amounts,
            'on_acc': self.on_acc,
            'state': self.state,
            'function': self.function,
            'tot_comp_cur': self.tot_comp_cur,
            'excl_dispute': self.excl_dispute,
            'date_time_print': self.date_time_print,
            'today': s,
            'pnames': self.plist(self.partner_id),
            'ptags': self.plist(self.analytic_tag_ids),
            'pptags': self.plist(self.category_id),
            'curname': cur,
            'filter_curname': self.currency_id.name,
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_sales_purch_ledger.html_report_pl_ledger', data=datas)

    @api.multi
    def ledger_pl_report_pdf(self):

        meet_date = fields.Datetime.from_string(self.today)
        s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id.name

        datas = {
            'partner_id': self.partner_id.ids,
            'category_id': self.category_id.ids,
            'user_id': self.user_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'sl_cred_acc_ids': self.sl_cred_acc_ids.ids,
            'Amounts': self.Amounts,
            'on_acc': self.on_acc,
            'state': self.state,
            'function': self.function,
            'tot_comp_cur': self.tot_comp_cur,
            'excl_dispute': self.excl_dispute,
            'date_time_print': self.date_time_print,
            'today': s,
            'pnames': self.plist(self.partner_id),
            'ptags': self.plist(self.analytic_tag_ids),
            'pptags': self.plist(self.category_id),
            'curname': cur,
            'filter_curname': self.currency_id.name,
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_sales_purch_ledger.pdf_report_pl_ledger', data=datas)

    def ledger_pl_report_xls(self):
        context = self._context
        filename = 'Purchase_ledger.xls'
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('Detalle')

        # data
        docs = {}
        domain = [('partner_id.supplier','=',True),('state','in',['open','paid']),('type','in',['in_invoice','in_refund'])]
        if self.date:
            dates = self.date
        else:
            dates = datetime.now().strftime('%Y-%m-%d')
        if self.state== 'open':
            domain.append(('date_invoice','<=',dates))
        else:
            domain.append(('date_due', '<=', dates))
        if self.partner_id:
            domain.append(('partner_id', 'in', list(self.partner_id._ids)))
        if self.category_id:
            domain.append(('partner_id.category_id', 'in', self.category_id))
        if self.user_id:
            domain.append(('user_id', 'in', self.user_id))
        if self.analytic_tag_ids:
            domain.append(('analytic_tag_ids', 'in', self.analytic_tag_ids))
        if self.currency_id:
            domain.append(('currency_id.id', '=', self.currency_id))
        if self.sl_cred_acc_ids:
            domain.append(('account_id', 'in', self.sl_cred_acc_ids))

        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="partner_id,date_invoice")
        partners = self.env['res.partner'].search([('supplier','=',True)],order="name").mapped("name")
        partners1 = self.env['res.partner'].search([('supplier','=',True)],order="name")

        partnersid = {}
        partnersacc = {}
        for p in partners1:
            partnersid.update({p.name:p})
            partnersacc.update({p.name:p.property_account_payable_id})

        #print partnersid
        #print partnersacc
        inv_to_delete = []
        p_array = {}
        for inv in invoices:
            if inv.payment_move_line_ids:
                for pay in inv.payment_move_line_ids:
                    if pay.date <= dates:
                        if self.Amounts == 'comp_cur':
                            cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id
                            date = datetime.now()
                            bal =  inv.currency_id.with_context(date=date).compute(pay.balance, cur)
                        else:
                            bal = pay.balance

                        if inv.id in p_array.keys():
                            p_array[inv.id] = p_array[inv.id] + bal
                        else:
                            p_array.update({inv.id:bal})

                if inv.id in p_array.keys():
                    if p_array[inv.id] >= inv.amount_total or p_array[inv.id] < 0:
                        inv_to_delete.append(inv)
                else:
                    p_array.update({inv.id: 0.0})
            else:
                p_array.update({inv.id: 0.0})

        #print p_array
        for itd in inv_to_delete:
            invoices -= itd

        # Titles
        index = 0
        worksheet.write(0, index, _('Supplier'))
        if self.function == 'overview':
            index += 1
            worksheet.write(0, index, _('Doc Type'))
            index += 1
            worksheet.write(0, index, _('Register Official No'))
            index += 1
            worksheet.write(0, index, _('Register Date'))
            index += 1
            worksheet.write(0, index, _('Invoice Due Date'))
            index += 1
            worksheet.write(0, index, _('Days'))
            index += 1
            worksheet.write(0, index, _('Inovice Total'))
            index += 1
            worksheet.write(0, index, _('Open Balance'))
            index += 1
            worksheet.write(0, index, _('Due Balance'))
            index += 1
            worksheet.write(0, index, _('Not Due Balance'))
            index += 1
            worksheet.write(0, index, _('On Account Total'))
            index += 1
            worksheet.write(0, index, _('Balance'))
            index += 1
        else:
            index += 1
            worksheet.write(0, index, _('Currency'))
            index += 1
            worksheet.write(0, index, _('Open Balance'))


        tot1 = tot2 = tot3 = tot4 = tot5 = tot6 = 0.0
        index = 2
        sign = 1

        inv_obj = self.env['account.invoice']
        matrix = {}
        a_cur = []
        for partner in partners:
            for o in invoices:
                if self.function == 'overview':
                    if partnersid[partner] == o.partner_id:
                        if o.type == 'in_refund':
                            sign = -1
                        else:
                            sign = 1
                        subindex = 0

                        worksheet.write(index, subindex, o.partner_id.name)
                        subindex += 1

                        worksheet.write(index, subindex, o.journal_document_type_id.document_type_id.report_name)
                        subindex += 1

                        worksheet.write(index, subindex, str(o.display_name))  # nro comprob
                        subindex += 1

                        worksheet.write(index, subindex, o.date_invoice)
                        subindex += 1

                        worksheet.write(index, subindex, o.date_due)
                        subindex += 1

                        worksheet.write(index, subindex, o.getdatedif(self.date,o.date_due,o.date_invoice))
                        subindex += 1

                        tmpv = o.amount_total_cur(o,self.Amounts)*sign
                        worksheet.write(index, subindex, tmpv)
                        tot1 += tmpv
                        subindex += 1

                        tmpv = (o.amount_total_cur(o,self.Amounts) - p_array[o.id])*sign
                        worksheet.write(index, subindex, tmpv)
                        tot2 += tmpv
                        subindex += 1

                        if o.getdatedif(self.date,o.date_due,o.date_invoice) < 0:
                            worksheet.write(index, subindex, tmpv)
                            subindex += 1
                            worksheet.write(index, subindex, "-")
                            tot3 += tmpv
                        else:
                            worksheet.write(index, subindex, "-")
                            subindex += 1
                            worksheet.write(index, subindex, tmpv)
                            tot4 += tmpv
                        subindex += 1

                        index += 1
            else:
                if inv_obj.has_invs(partnersid[partner],invoices):
                    totcur = inv_obj.getopenvals_ob(partnersid[partner],invoices,p_array)
                    for t in totcur:
                        if t not in a_cur:
                            a_cur.append(t)

                        if not partner in matrix.keys():
                            matrix[partner] = {t:totcur[t]}
                        else:
                            if not t in matrix[partner].keys():
                                matrix[partner].update({t:totcur[t]})
                            else:
                                matrix[partner][t] += totcur[t]



            if self.function == 'overview':
                tmpv = invoiceModel.get_outstanding_report(partnersid[partner], partnersacc[partner], self.date)
                if tmpv != 0:
                    apgs = invoiceModel.get_outstanding_report_apg(partnersid[partner], partnersacc[partner], self.date)
                    for apg in apgs:
                        subindex = 0
                        worksheet.write(index, subindex, partner)
                        subindex += 1

                        worksheet.write(index, subindex, apg.payment_id.receiptbook_id.document_type_id.report_name)
                        subindex += 1

                        worksheet.write(index, subindex, apg.payment_id.payment_group_id.name)
                        subindex += 1

                        worksheet.write(index, subindex, apg.payment_id.payment_date)
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, "-")
                        subindex += 1

                        worksheet.write(index, subindex, -apg.amount_residual)
                        subindex += 1
                        tot5 += -apg.amount_residual

                        worksheet.write(index, subindex, "-")
                        subindex += 1
                        index += 1

        print a_cur
        print matrix
        subindex = 0
        if self.function == 'overview':
            worksheet.write(index, subindex, _("Totales"))
            subindex = 6
            worksheet.write(index, subindex, tot1)
            subindex += 1
            worksheet.write(index, subindex, tot2)
            subindex += 1
            worksheet.write(index, subindex, tot3)
            subindex += 1
            worksheet.write(index, subindex, tot4)
            subindex += 1
            worksheet.write(index, subindex, tot5)
            subindex += 1
            worksheet.write(index, subindex, (tot2+tot5))
            subindex += 1
        else:
            for me in matrix:
                subindex = 0
                worksheet.write(index, subindex, me)
                subindex += 1
                for cur in a_cur:
                    worksheet.write(index, subindex, cur)
                    subindex += 1
                    if cur in matrix[me].keys():
                        worksheet.write(index, subindex, matrix[me][cur])
                    else:
                        worksheet.write(index, subindex, " ")
                    subindex += 1



                index += 1


        fp = StringIO()
        workbook.save(fp)
        export_id = self.env['excel.extended'].create(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename}).id
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'excel.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }


class report_vitt_sales_purch_ledger_html_report_pl_ledger(models.Model):
    _name = "report.vitt_sales_purch_ledger.html_report_pl_ledger"

    def render_html(self,docids, data=None):
        docs = {}
        domain = [('partner_id.supplier','=',True),('state','in',['open','paid']),('type','in',['in_invoice','in_refund'])]
        if data['date']:
            dates = data['date']
        else:
            dates = datetime.now().strftime('%Y-%m-%d')
        if data['state']== 'open':
            domain.append(('date_invoice','<=',dates))
        else:
            domain.append(('date_due', '<=', dates))
        if data['partner_id']:
            domain.append(('partner_id.id', 'in', data['partner_id']))
        if data['category_id']:
            domain.append(('partner_id.category_id', 'in', data['category_id']))
        if data['user_id']:
            domain.append(('user_id', 'in', [data['user_id']]))
        if data['analytic_tag_ids']:
            domain.append(('analytic_tag_ids', 'in', data['analytic_tag_ids']))
        if data['currency_id']:
            domain.append(('currency_id.id', '=', data['currency_id']))
        if data['sl_cred_acc_ids']:
            domain.append(('account_id', 'in', data['sl_cred_acc_ids']))

        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="partner_id,date_invoice")
        partners = self.env['res.partner'].search([('supplier','=',True)],order="name").mapped("name")
        partners1 = self.env['res.partner'].search([('supplier','=',True)],order="name")

        partnersid = {}
        partnersacc = {}
        for p in partners1:
            partnersid.update({p.name:p})
            partnersacc.update({p.name:p.property_account_payable_id})

        #print partnersid
        #print partnersacc
        inv_to_delete = []
        p_array = {}
        for inv in invoices:
            if inv.payment_move_line_ids:
                for pay in inv.payment_move_line_ids:
                    if pay.date <= dates:
                        if data['Amounts'] == 'comp_cur':
                            cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id
                            date = datetime.now()
                            bal =  inv.currency_id.with_context(date=date).compute(pay.balance, cur)
                        else:
                            bal = pay.balance

                        if inv.id in p_array.keys():
                            p_array[inv.id] = p_array[inv.id] + bal
                        else:
                            p_array.update({inv.id:bal})

                if inv.id in p_array.keys():
                    if p_array[inv.id] >= inv.amount_total or p_array[inv.id] < 0:
                        inv_to_delete.append(inv)
                else:
                    p_array.update({inv.id: 0.0})
            else:
                if inv.type != 'in_refund':
                    p_array.update({inv.id: 0.0})
                else:
                    inv_to_delete.append(inv)

        #print p_array
        for itd in inv_to_delete:
            invoices -= itd

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_sales_purch_ledger.html_report_pl_ledger')
        docargs = {
            'doc_ids': invoices._ids,
            'doc_model': report.model,
            'docs': invoices,
            'payments': p_array,
            'data': data,
            'partners': partners,
            'partnersid': partnersid,
            'partnersacc': partnersacc,
        }
        return self.env['report'].render('vitt_sales_purch_ledger.qweb_report_pl_ledger', docargs)

class report_vitt_sales_purch_ledger_pdf_report_pl_ledger(models.Model):
    _inherit = "report.vitt_sales_purch_ledger.html_report_pl_ledger"
    _name = "report.vitt_sales_purch_ledger.pdf_report_pl_ledger"


class report_vitt_sales_purch_ledger_html_report_sl_ledger(models.Model):
    _name = "report.vitt_sales_purch_ledger.html_report_sl_ledger"

    def render_html(self,docids, data=None):
        docs = {}
        domain = [('partner_id.customer','=',True),('state','in',['open','paid']),('type','in',['out_invoice','out_refund'])]
        if data['date']:
            dates = data['date']
        else:
            dates = datetime.now().strftime('%Y-%m-%d')
        if data['state']== 'open':
            domain.append(('date_invoice','<=',dates))
        else:
            domain.append(('date_due', '<=', dates))
        if data['partner_id']:
            domain.append(('partner_id', 'in', data['partner_id']))
        if data['category_id']:
            domain.append(('partner_id.category_id', 'in', data['category_id']))
        if data['user_id']:
            domain.append(('user_id', 'in', [data['user_id']]))
        if data['analytic_tag_ids']:
            domain.append(('analytic_tag_ids', 'in', data['analytic_tag_ids']))
        if data['currency_id']:
            domain.append(('currency_id.id', '=', data['currency_id']))
        if data['sl_cred_acc_ids']:
            domain.append(('account_id', 'in', data['sl_cred_acc_ids']))
        if data['team']:
            domain.append(('team_id', '=', data['team']))

        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="partner_id,date_invoice")
        partners = self.env['res.partner'].search([('customer','=',True)],order="name").mapped("name")
        partners1 = self.env['res.partner'].search([('customer','=',True)],order="name")

        partnersid = {}
        partnersacc = {}
        for p in partners1:
            partnersid.update({p.name:p})
            partnersacc.update({p.name:p.property_account_receivable_id})

        #print invoices
        inv_to_delete = []
        p_array = {}
        for inv in invoices:
            if inv.payment_move_line_ids:
                for pay in inv.payment_move_line_ids:
                    if pay.date <= dates:
                        if data['Amounts'] == 'comp_cur':
                            cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id
                            date = datetime.now()
                            bal =  -inv.currency_id.with_context(date=date).compute(pay.balance, cur)
                        else:
                            bal = -pay.balance

                        if inv.id in p_array.keys():
                            p_array[inv.id] = p_array[inv.id] + bal
                        else:
                            p_array.update({inv.id:bal})

                if inv.id in p_array.keys():
                    if p_array[inv.id] >= inv.amount_total or p_array[inv.id] < 0:
                        inv_to_delete.append(inv)
                else:
                    p_array.update({inv.id: 0.0})
            else:
                if inv.type != 'out_refund':
                    p_array.update({inv.id: 0.0})
                else:
                    inv_to_delete.append(inv)

        #print p_array
        for itd in inv_to_delete:
            invoices -= itd

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_sales_purch_ledger.html_report_sl_ledger')
        docargs = {
            'doc_ids': invoices._ids,
            'doc_model': report.model,
            'docs': invoices,
            'payments': p_array,
            'data': data,
            'partners': partners,
            'partnersid': partnersid,
            'partnersacc': partnersacc,
        }
        return self.env['report'].render('vitt_sales_purch_ledger.qweb_report_sl_ledger', docargs)

class report_vitt_sales_purch_ledger_pdf_report_sl_ledger(models.Model):
    _inherit = "report.vitt_sales_purch_ledger.html_report_sl_ledger"
    _name = "report.vitt_sales_purch_ledger.pdf_report_sl_ledger"


class ReportSlLedger(models.TransientModel):
    _name = "report.sl.ledger"

    partner_id = fields.Many2many('res.partner',string="customer",translate=True,domain="[('customer','=',True)]")
    category_id = fields.Many2many('res.partner.category', column1='partner_id',column2='category_id',
                                   string='Partner Tags',translate=True)
    user_id = fields.Many2one('res.users',string="Sales Person",translate=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag',string="Analytic Tags (Header)",translate=True)
    currency_id = fields.Many2one('res.currency',string="Currency",translate=True)
    date = fields.Date(string='To Date', required=True,default=datetime.now().strftime('%Y-%m-%d'))
    sl_cred_acc_ids = fields.Many2many('account.account',domain=[('user_type_id.type','=','receivable')],string="Debtors Account",translate=True)
    Amounts = fields.Selection([('comp_cur', 'Company Currency'),('inv_cur', 'Invoice Currency')],
                               string='Amounts', default='comp_cur', translate=True)
    on_acc = fields.Selection([('include', 'Include on Account'),('only', 'Only on Account'),('skip', 'Skip on Account')],
                               string='On Account', default='include', translate=True)
    state = fields.Selection([('open', 'Open'),('overdue', 'Overdue')],string='State', default='open', translate=True)
    function = fields.Selection([('overview', 'Overview'),('open_balance', 'Open Balance')],
                               string='Function', default='overview', translate=True)
    tot_comp_cur = fields.Boolean(string="Show totals in Company Currency", default=True,translate=True)
    excl_dispute = fields.Boolean(string="Excluir Facturas Cuestionadas",translate=True)
    date_time_print = fields.Boolean(string="Print report print Date & Time", default=True,translate=True)
    today = fields.Datetime(default=lambda self: fields.Datetime.now())
    team_id = fields.Many2one('crm.team', string="Sales Team", translate=True)

    def plist(self,plist):
        res = ""
        for p in plist:
            res += ',' + p.name
        return res

    @api.multi
    def ledger_sl_report_html(self):

        meet_date = fields.Datetime.from_string(self.today)
        s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id.name

        datas = {
            'partner_id': self.partner_id.ids,
            'category_id': self.category_id.ids,
            'user_id': self.user_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'sl_cred_acc_ids': self.sl_cred_acc_ids.ids,
            'Amounts': self.Amounts,
            'on_acc': self.on_acc,
            'state': self.state,
            'function': self.function,
            'tot_comp_cur': self.tot_comp_cur,
            'excl_dispute': self.excl_dispute,
            'date_time_print': self.date_time_print,
            'today': s,
            'pnames': self.plist(self.partner_id),
            'ptags': self.plist(self.analytic_tag_ids),
            'pptags': self.plist(self.category_id),
            'team': self.team_id.id,
            'team_m': self.team_id.name,
            'curname': cur,
            'filter_curname': self.currency_id.name,
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_sales_purch_ledger.html_report_sl_ledger', data=datas)

    @api.multi
    def ledger_sl_report_pdf(self):

        meet_date = fields.Datetime.from_string(self.today)
        s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        cur = self.env['res.company']._company_default_get('vitt_sales_purch_ledger').currency_id.name

        datas = {
            'partner_id': self.partner_id.ids,
            'category_id': self.category_id.ids,
            'user_id': self.user_id.id,
            'analytic_tag_ids': self.analytic_tag_ids.ids,
            'currency_id': self.currency_id.id,
            'date': self.date,
            'sl_cred_acc_ids': self.sl_cred_acc_ids.ids,
            'Amounts': self.Amounts,
            'on_acc': self.on_acc,
            'state': self.state,
            'function': self.function,
            'tot_comp_cur': self.tot_comp_cur,
            'excl_dispute': self.excl_dispute,
            'date_time_print': self.date_time_print,
            'today': s,
            'pnames': self.plist(self.partner_id),
            'ptags': self.plist(self.analytic_tag_ids),
            'pptags': self.plist(self.category_id),
            'team': self.team_id.id,
            'team_m': self.team_id.name,
            'curname': cur,
            'filter_curname': self.currency_id.name,
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_sales_purch_ledger.pdf_report_sl_ledger', data=datas)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def getdatedif(self,date1,date2,date3):
        import datetime
        if date2:
            date1 = datetime.datetime.strptime(date1, '%Y-%m-%d').date()
            date2 = datetime.datetime.strptime(date2, '%Y-%m-%d').date()
        else:
            date1 = datetime.datetime.strptime(date1, '%Y-%m-%d').date()
            date2 = datetime.datetime.strptime(date3, '%Y-%m-%d').date()
        td = date2 - date1
        return td.days

    #purchase
    def get_outstanding_report(self,pid,accid,todate,cur=False):
        amount_to_show = 0.0
        domain = [('account_id', '=', accid.id),('partner_id', '=', self.env['res.partner']._find_accounting_partner(pid).id),
                  ('reconciled', '=', False), ('amount_residual', '!=', 0.0),('credit', '=', 0), ('debit', '>', 0),('date','<=',todate)]
        lines = self.env['account.move.line'].search(domain)
        currency_id = self.currency_id
        if len(lines) != 0:
            for line in lines:
                # get the outstanding residual value in invoice currency
                if line.currency_id and line.currency_id == self.company_id.currency_id:
                    amount_to_show += abs(line.amount_residual_currency)
                else:
                    if not cur:
                        amount_to_show += line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), self.company_id.currency_id)
                    else:
                        amount_to_show += line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), cur)


        return -amount_to_show

    def get_outstanding_report_apg(self,pid,accid,todate):
        domain = [('account_id', '=', accid.id),('partner_id', '=', self.env['res.partner']._find_accounting_partner(pid).id),
                  ('reconciled', '=', False), ('amount_residual', '!=', 0.0),('credit', '=', 0), ('debit', '>', 0),('date','<=',todate)]
        lines = self.env['account.move.line'].search(domain)
        return lines


    def getopenbalancet(self,lastp,docs,payments,amounts):
        tot = 0.0
        for doc in docs:
            if doc.partner_id == lastp:
                if amounts == 'comp_cur':
                    cur = self.company_id.currency_id
                    date = datetime.now()
                    tot +=  doc.currency_id.with_context(date=date).compute(doc.amount_total, cur) - payments[doc.id]
                else:
                    tot += doc.amount_total - payments[doc.id]
        return tot

    def getopenduet(self,lastp,docs,payments,date1,amounts):
        tot = 0.0
        for doc in docs:
            if doc.partner_id == lastp and self.getdatedif(date1,doc.date_due,doc.date_invoice) < 0:
                if amounts == 'comp_cur':
                    cur = self.company_id.currency_id
                    date = datetime.now()
                    tot +=  doc.currency_id.with_context(date=date).compute(doc.amount_total, cur) - payments[doc.id]
                else:
                    tot += doc.amount_total - payments[doc.id]
        return tot

    def getnotopenduet(self,lastp,docs,payments,date1,amounts):
        tot = 0.0
        for doc in docs:
            if doc.partner_id == lastp and self.getdatedif(date1,doc.date_due,doc.date_invoice) >= 0:
                if amounts == 'comp_cur':
                    cur = self.company_id.currency_id
                    date = datetime.now()
                    tot +=  doc.currency_id.with_context(date=date).compute(doc.amount_total, cur) - payments[doc.id]
                else:
                    tot += doc.amount_total - payments[doc.id]
        return tot

    def amount_total_cur(self,inv,amounts):
        if amounts == 'comp_cur':
            cur = self.company_id.currency_id
            date = datetime.now()
            return inv.currency_id.with_context(date=date).compute(inv.amount_total, cur)
        else:
            return inv.amount_total

    def get_ps_sl_totals(self,docs,date,payments,amounts,cur=False,totcur=False,partners=False,partnersid=False,partnersacc=False,partner_id=False):
        t_list = [0,0,0,0]
        p_id = ""
        if cur:
            curr = self.env['res.currency'].search([('id','=',cur)])
        else:
            curr=False
        if totcur:
            amounts = 'comp_cur'

        for doc in docs:
            if doc.partner_id != p_id:
                p_id = doc.partner_id
                #t_list[0] += doc.get_outstanding_report(partner,partner.property_account_payable_id,date,curr)
                t_list[1] += doc.getopenbalancet(doc.partner_id,docs,payments,amounts)
                t_list[2] += doc.getopenduet(doc.partner_id,docs,payments,date,amounts)
                t_list[3] += doc.getnotopenduet(doc.partner_id,docs,payments,date,amounts)
        if not partner_id:
            for partner in partners:
                tmpv = doc.get_outstanding_report(partnersid[partner],partnersacc[partner],date,curr)
                t_list[0] += tmpv
                t_list[1] += tmpv
        else:
            for partner in partner_id:
                p = self.env['res.partner'].browse(partner)
                tmpv = doc.get_outstanding_report(p,p.property_account_payable_id,date,curr)
                t_list[0] += tmpv
                t_list[1] += tmpv

        return t_list

    def getopenvals_ob(self,lastp,docs,payments):
        acurvals = {}
        for doc in docs:
            if doc.partner_id == lastp:
                tmpv =  doc.residual
                if not doc.currency_id.name in acurvals.keys():
                    acurvals.update({doc.currency_id.name:tmpv})
                else:
                    acurvals[doc.currency_id.name] += tmpv

        return acurvals

    def has_invs(self,name,docs):
        for doc in docs:
            if doc.partner_id == name:
                return True
        return False

    def get_filter(self,partnerid, filterid):
        if not filterid:
            return True
        if partnerid in filterid:
            return True
        return False

    #sales
    def get_ps_sl_totals2(self,docs,date,payments,amounts,cur=False,totcur=False,partners=False,partnersid=False,partnersacc=False,partner_id=False):
        t_list = [0,0,0,0]
        p_id = ""
        if cur:
            curr = self.env['res.currency'].search([('id','=',cur)])
        else:
            curr=False
        if totcur:
            amounts = 'comp_cur'

        for doc in docs:
            if doc.partner_id != p_id:
                p_id = doc.partner_id
                #t_list[0] += doc.get_outstanding_report_sl(doc.partner_id,doc.account_id,date,curr)
                t_list[1] += doc.getopenbalancet(doc.partner_id,docs,payments,amounts)
                t_list[2] += doc.getopenduet(doc.partner_id,docs,payments,date,amounts)
                t_list[3] += doc.getnotopenduet(doc.partner_id,docs,payments,date,amounts)
        if not partner_id:
            for partner in partners:
                tmpv = doc.get_outstanding_report(partnersid[partner],partnersacc[partner],date,curr)
                t_list[0] += tmpv
                t_list[1] += tmpv
        else:
            for partner in partner_id:
                p = self.env['res.partner'].browse(partner)
                tmpv = doc.get_outstanding_report(p,p.property_account_receivable_id,date,curr)
                t_list[0] += tmpv
                t_list[1] += tmpv

        return t_list

    def get_outstanding_report_sl(self,pid,accid,todate,cur=False):
        amount_to_show = 0.0
        domain = [('account_id', '=', accid.id),('partner_id', '=', self.env['res.partner']._find_accounting_partner(pid).id),
                  ('reconciled', '=', False), ('amount_residual', '!=', 0.0),('debit', '=', 0), ('credit', '>', 0),('date','<=',todate)]
        lines = self.env['account.move.line'].search(domain)

        currency_id = self.currency_id
        if len(lines) != 0:
            for line in lines:
                # get the outstanding residual value in invoice currency
                if line.currency_id and line.currency_id == self.company_id.currency_id:
                    amount_to_show += abs(line.amount_residual_currency)
                else:
                    if not cur:
                        amount_to_show += line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), self.company_id.currency_id)
                    else:
                        amount_to_show += line.company_id.currency_id.with_context(date=line.date).compute(
                            abs(line.amount_residual), cur)

        return -amount_to_show

    def get_outstanding_report_apg_sl(self,pid,accid,todate):
        domain = [('account_id', '=', accid.id),('partner_id', '=', self.env['res.partner']._find_accounting_partner(pid).id),
                  ('reconciled', '=', False), ('amount_residual', '!=', 0.0),('debit', '=', 0), ('credit', '>', 0),('date','<=',todate)]
        lines = self.env['account.move.line'].search(domain)
        return lines
