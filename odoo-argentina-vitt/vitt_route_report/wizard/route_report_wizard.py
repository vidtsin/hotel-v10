from odoo import http, models, fields, api, _
from datetime import datetime
from datetime import timedelta
import xlwt
from cStringIO import StringIO
import base64

class sales_reports(models.TransientModel):
    _name = 'catanese.report.route'

    date = fields.Date(string='Date',required=True,default=datetime.now().strftime('%Y-%m-%d'),translate=True)
    freight = fields.Many2one('freight.freight',string="Freight",translate=True,required=True)
    hours = fields.Boolean(string="Show Hours")

    def Print_to_excel(self):
        context = self._context
        filename= 'Informe_de_Ruta.xls'
        workbook= xlwt.Workbook(encoding="UTF-8")
        worksheet= workbook.add_sheet('Detalle')

        #data
        dates = datetime.strptime(self.date, "%Y-%m-%d").date()
        d1 = datetime.strftime(dates, "%Y-%m-%d 00:00:00")
        d2 = datetime.strftime(dates, "%Y-%m-%d 23:59:59")
        domain = [
            ('freight_id.name','=',self.freight.name),
            ('min_date', '>=', d1), ('min_date', '<=', d2),
            ('state','in',['waiting','confirmed','partially_available','assigned']),
        ]
        invoiceModel = self.env['stock.picking']
        invoices = invoiceModel.search(domain,order="del_sequence")

        hour = {}
        tot_pack = 0
        tot_w = tot_sw = 0.0
        for pick in invoices:
            tot_pack += pick.pack_ids_quant(pick)
            tot_w += pick.weight
            tot_sw += pick.shipping_weight
            meet_date = fields.Datetime.from_string(pick.min_date)
            s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
            s = s.split(" ")
            hour.update({pick.id:s[-1]})

        tot1 = tot2 = tot3 = tot4 = tot5 = tot6 = 0

        # Titles
        index = 0
        worksheet.write(0,index,_('Hoja de Ruta'))

        index = 0
        worksheet.write(1,index,_('Flete'))
        index += 1
        worksheet.write(1,index,self.freight.name)

        index = 0
        worksheet.write(2,index,_('cantidad de paquetes'))
        index += 1
        worksheet.write(2,index,tot_pack)

        index = 0
        worksheet.write(3,index,_('Peso total'))
        index += 1
        worksheet.write(3,index,tot_sw)

        index = 0
        if self.hours == True:
            worksheet.write(6, index, _('Hora'))
            index += 1
        worksheet.write(6,index,_('Direccion'))
        index += 1
        worksheet.write(6,index,_('Telefono'))
        index += 1
        worksheet.write(6,index,_('Remito'))
        index += 1
        worksheet.write(6,index,_('Bultos'))
        index += 1

        index = 7
        for o in invoices:
            subindex = 0
            if self.hours == True:
                worksheet.write(index, subindex, hour[o.id])
                subindex += 1
            if o.transport_company_id.id != False:
                worksheet.write(index, subindex, str(o.transport_company_id.street) + " - " +
                                                str(o.transport_company_id.street2) + " - " +
                                                str(o.transport_company_id.city) + " - " +
                                                str(o.transport_company_id.country_id.name))
            else:
                worksheet.write(index, subindex, str(o.partner_id.street) + " - " +
                                                str(o.partner_id.street2) + " - " +
                                                str(o.partner_id.city) + " - " +
                                                str(o.partner_id.country_id.name))
            subindex += 1

            if o.transport_company_id.id != False:
                worksheet.write(index, subindex, str(o.transport_company_id.phone) + " - " + str(o.transport_company_id.mobile))
            else:
                worksheet.write(index, subindex, str(o.partner_id.phone) + " - " + str(o.partner_id.mobile))
            subindex += 1


            worksheet.write(index, subindex,o.name)
            subindex += 1

            worksheet.write(index, subindex, o.number_of_packages)
            subindex += 1

            index += 1
            subindex = 0
            worksheet.write(index, subindex,_('Notas'))
            subindex += 1
            worksheet.write(index, subindex,o.transport_note)
            subindex += 1

            index += 1

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

    @api.multi
    def ex_routereport(self):
        datas = {
          'date': self.date,
          'freight': self.freight.name,
          'hours': self.hours,
        }
        return self.env['report'].with_context(landscape=True).get_action(self,'vitt_route_report.routereport', data=datas)

class report_vitt_sales_reports_reportvat(models.Model):
    _name = "report.vitt_route_report.routereport"

    def render_html(self,docids, data=None):

        dates = datetime.strptime(data['date'], "%Y-%m-%d").date()
        d1 = datetime.strftime(dates, "%Y-%m-%d 00:00:00")
        d2 = datetime.strftime(dates, "%Y-%m-%d 23:59:59")
        domain = [
            ('freight_id.name','=',data['freight']),
            ('min_date', '>=', d1), ('min_date', '<=', d2),
            ('state','in',['waiting','confirmed','partially_available','assigned']),
        ]
        invoiceModel = self.env['stock.picking']
        invoices = invoiceModel.search(domain,order="del_sequence")

        hour = {}
        tot_pack = 0
        tot_w = tot_sw = 0.0
        for pick in invoices:
            tot_pack += pick.pack_ids_quant(pick)
            tot_w += pick.weight
            tot_sw += pick.shipping_weight
            meet_date = fields.Datetime.from_string(pick.min_date)
            s = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
            s = s.split(" ")
            hour.update({pick.id:s[-1]})

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_route_report.bonusreport')
        docargs = {
            'doc_ids': invoices._ids,
            'doc_model': report.model,
            'docs': invoices,
            'date': data['date'],
            'freight': data['freight'],
            'hours': data['hours'],
            'hour': hour,
            'tot_pack': tot_pack,
            'tot_w': tot_w,
            'tot_sw': tot_sw,
        }
        return self.env['report'].render('vitt_route_report.routereport', docargs)

