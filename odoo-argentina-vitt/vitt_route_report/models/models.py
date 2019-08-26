# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def pack_ids_cons(self,doc):
        res = self.env['stock.quant.package']
        for reg in doc.pack_operation_product_ids:
            if not reg.result_package_id in res:
                res += reg.result_package_id
        return res

    def pack_ids_quant(self,doc):
        res = self.env['stock.quant.package']
        for reg in doc.pack_operation_product_ids:
            if not reg.result_package_id in res:
                res += reg.result_package_id
        return len(res)

    def get_pick_from_order(self,doc):
        pickings = self.env['sale.order'].search([('procurement_group_id.id','=',doc.group_id.id)])
        for pick in pickings:
            return pick